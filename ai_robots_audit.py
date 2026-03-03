from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Optional
from urllib.parse import urlparse

import requests


KNOWNAGENTS_LIST_URL = "https://knownagents.com/agents"
KNOWNAGENTS_AGENT_URL = "https://knownagents.com/agents/{slug}"


@dataclass(frozen=True)
class RobotsRule:
    directive: Literal["allow", "disallow"]
    path: str


@dataclass
class RobotsGroup:
    user_agents: list[str]
    rules: list[RobotsRule]


@dataclass(frozen=True)
class RobotsFetchResult:
    final_url: str
    status_code: int
    text: str
    error: Optional[str] = None


def _http_get_text(url: str, *, timeout_s: float = 15.0) -> str:
    resp = requests.get(
        url,
        timeout=timeout_s,
        headers={
            "User-Agent": "ai-robots-audit/1.0 (+https://example.invalid)",
            "Accept": "text/html,text/plain,*/*",
        },
    )
    resp.raise_for_status()
    return resp.text


def _http_get_robots(domain: str, *, timeout_s: float = 15.0) -> RobotsFetchResult:
    last_exc: Optional[str] = None
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/robots.txt"
        try:
            resp = requests.get(
                url,
                timeout=timeout_s,
                headers={
                    "User-Agent": "ai-robots-audit/1.0 (+https://example.invalid)",
                    "Accept": "text/plain,text/*;q=0.9,*/*;q=0.1",
                },
                allow_redirects=True,
            )
            return RobotsFetchResult(
                final_url=str(resp.url),
                status_code=int(resp.status_code),
                text=resp.text if resp.text is not None else "",
                error=None,
            )
        except Exception as e:  # noqa: BLE001 - CLI tool; capture error and continue
            last_exc = f"{type(e).__name__}: {e}"
    return RobotsFetchResult(
        final_url=f"https://{domain}/robots.txt",
        status_code=0,
        text="",
        error=last_exc or "Unknown error",
    )


def parse_knownagents_slugs(list_html: str) -> list[str]:
    # Extract "/agents/<slug>" links, excluding "/agents" itself.
    slugs = set(re.findall(r'href="https?://knownagents\\.com/agents/([a-z0-9-]+)"', list_html))
    slugs |= set(re.findall(r'href="/agents/([a-z0-9-]+)"', list_html))
    slugs.discard("")
    return sorted(slugs)


def extract_user_agents_from_agent_page(agent_html: str) -> list[str]:
    """
    Prefer the canonical robots.txt snippet on the agent page:
      User-agent: GPTBot # https://knownagents.com/agents/gptbot
    Falls back to parsing the "User Agent String" example for a token-like name.
    """
    agents: list[str] = []

    # 1) Try to parse "User-agent:" lines from the robots example blocks.
    for m in re.finditer(r"(?im)^\\s*User-agent\\s*:\\s*([^\\s#]+)", agent_html):
        token = m.group(1).strip()
        if token and token not in agents:
            agents.append(token)

    if agents:
        return agents

    # 2) Fallback: extract token from example UA string like "... compatible; GPTBot/1.3; ..."
    # This is heuristic: capture a token before '/' that looks like a bot name.
    m2 = re.search(r"compatible;\\s*([A-Za-z0-9._-]+)\\s*/\\s*[0-9]", agent_html)
    if m2:
        return [m2.group(1)]

    return []


def fetch_knownagents_user_agent_tokens(
    *,
    agent_types: list[str],
    max_agents: int,
    timeout_s: float,
) -> dict[str, dict[str, Any]]:
    """
    Returns a mapping:
      token -> { "token": str, "slugs": [...], "source": "knownagents", "agent_urls": [...] }
    """
    token_map: dict[str, dict[str, Any]] = {}

    if not agent_types:
        agent_types = [""]

    seen_slugs: set[str] = set()
    slugs: list[str] = []
    for t in agent_types:
        url = KNOWNAGENTS_LIST_URL if not t else f"{KNOWNAGENTS_LIST_URL}?agent_type_url_slug={t}"
        html = _http_get_text(url, timeout_s=timeout_s)
        for s in parse_knownagents_slugs(html):
            if s not in seen_slugs:
                seen_slugs.add(s)
                slugs.append(s)
            if len(slugs) >= max_agents:
                break
        if len(slugs) >= max_agents:
            break

    for slug in slugs:
        url = KNOWNAGENTS_AGENT_URL.format(slug=slug)
        try:
            html = _http_get_text(url, timeout_s=timeout_s)
        except Exception:  # noqa: BLE001
            continue
        tokens = extract_user_agents_from_agent_page(html)
        for token in tokens:
            entry = token_map.setdefault(
                token,
                {"token": token, "slugs": [], "agent_urls": [], "source": "knownagents"},
            )
            entry["slugs"].append(slug)
            entry["agent_urls"].append(url)

    return token_map


def parse_robots_txt(text: str) -> list[RobotsGroup]:
    groups: list[RobotsGroup] = []
    current: Optional[RobotsGroup] = None

    def ensure_group() -> RobotsGroup:
        nonlocal current
        if current is None:
            current = RobotsGroup(user_agents=[], rules=[])
            groups.append(current)
        return current

    for raw_line in text.splitlines():
        # Strip comments (robots.txt comments start with '#')
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().lower()
        value = v.strip()

        if key == "user-agent":
            # If we already have rules in the current group, start a new group.
            if current is not None and current.rules:
                current = None
            g = ensure_group()
            if value:
                g.user_agents.append(value)
            continue

        if key in ("allow", "disallow"):
            g = ensure_group()
            directive = "allow" if key == "allow" else "disallow"
            # Disallow with empty value means allow all in the group; represent as empty path rule.
            g.rules.append(RobotsRule(directive=directive, path=value))

    # Drop empty groups (no user-agent)
    return [g for g in groups if g.user_agents]


def _ua_matches(group_uas: Iterable[str], token: str) -> tuple[bool, bool]:
    token_l = token.lower()
    any_exact = False
    any_wildcard = False
    for ua in group_uas:
        ua_l = ua.lower()
        if ua_l == "*":
            any_wildcard = True
        if ua_l == token_l:
            any_exact = True
    return any_exact, any_wildcard


@dataclass(frozen=True)
class RobotsDecision:
    allowed: bool
    matched_group_uas: list[str]
    rule_source: Literal["explicit", "wildcard", "none"]
    matched_rule: Optional[RobotsRule]


def _normalize_domain(raw: str) -> str:
    s = (raw or "").strip()
    if not s or s.startswith("#"):
        return ""

    # Accept either plain domains or full URLs.
    if "://" in s:
        try:
            u = urlparse(s)
            s = u.netloc or u.path
        except Exception:  # noqa: BLE001
            pass

    s = s.strip().strip("/")
    # Remove trailing path if someone pasted "example.com/foo"
    if "/" in s:
        s = s.split("/", 1)[0]
    return s


def _rule_matches(path: str, rule_path: str) -> bool:
    # Empty "Disallow:" means allow all; treat as match-all.
    if rule_path == "":
        return True

    # Support common patterns:
    # - '*' matches any string
    # - trailing '$' means "must end here"
    if "*" in rule_path or rule_path.endswith("$"):
        anchored = rule_path.endswith("$")
        pat = rule_path[:-1] if anchored else rule_path
        pat = re.escape(pat).replace("\\*", ".*")
        rx = f"^{pat}$" if anchored else f"^{pat}"
        try:
            return re.match(rx, path) is not None
        except re.error:
            return path.startswith(rule_path.replace("$", ""))

    return path.startswith(rule_path)


def _rule_specificity(rule_path: str) -> int:
    return len((rule_path or "").replace("*", "").replace("$", ""))


def decide_access(groups: list[RobotsGroup], token: str, path: str) -> RobotsDecision:
    explicit_groups: list[RobotsGroup] = []
    wildcard_groups: list[RobotsGroup] = []
    for g in groups:
        exact, wild = _ua_matches(g.user_agents, token)
        if exact:
            explicit_groups.append(g)
        elif wild:
            wildcard_groups.append(g)

    chosen_groups: list[RobotsGroup] = explicit_groups if explicit_groups else wildcard_groups
    if not chosen_groups:
        return RobotsDecision(
            allowed=True,
            matched_group_uas=[],
            rule_source="none",
            matched_rule=None,
        )

    # Robots matching: longest path wins; tie -> Allow wins over Disallow.
    best: Optional[RobotsRule] = None
    best_len = -1
    best_allow = False

    for g in chosen_groups:
        for r in g.rules:
            rule_path = r.path or ""
            if not _rule_matches(path, rule_path):
                continue
            l = _rule_specificity(rule_path)
            is_allow = r.directive == "allow"
            if l > best_len or (l == best_len and is_allow and not best_allow):
                best = r
                best_len = l
                best_allow = is_allow

    # If no matching rules, default allow within that group.
    if best is None:
        allowed = True
    else:
        if best.directive == "allow":
            allowed = True
        else:
            # Disallow with empty path means allow all (per common interpretation).
            allowed = (best.path == "")

    return RobotsDecision(
        allowed=allowed,
        matched_group_uas=sorted({ua for g in chosen_groups for ua in g.user_agents}),
        rule_source="explicit" if explicit_groups else "wildcard",
        matched_rule=best,
    )


def classify(decision: RobotsDecision) -> str:
    if decision.rule_source == "explicit":
        return "Explicitly Allowed" if decision.allowed else "Explicitly Blocked"
    if decision.rule_source == "wildcard":
        return "Wildcard Rule (Allowed)" if decision.allowed else "Wildcard Rule (Blocked)"
    return "No Matching Rules (Implicitly Allowed)"


def _split_csv_arg(v: Optional[str]) -> list[str]:
    if not v:
        return []
    parts = [p.strip() for p in v.split(",")]
    return [p for p in parts if p]


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Audit robots.txt rules for AI agents.")
    p.add_argument("--domains", help="Comma-separated list of domains (no scheme).")
    p.add_argument("--domains-file", help="File containing domains, one per line.")
    p.add_argument(
        "--agents",
        help="Comma-separated list of agent tokens (e.g. GPTBot,ClaudeBot,Google-Extended,CCBot).",
    )
    p.add_argument(
        "--knownagents-types",
        default="",
        help="Comma-separated Known Agents type slugs (e.g. ai-data-scraper,ai-search-crawler). Empty = all.",
    )
    p.add_argument("--max-agents", type=int, default=50, help="Max agents to pull from Known Agents.")
    p.add_argument("--path", default="/", help="Path to evaluate (default: /).")
    p.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds.")
    p.add_argument("--out-json", default="report.json", help="Output JSON file path.")
    p.add_argument("--out-csv", default="report.csv", help="Output CSV file path.")
    args = p.parse_args(argv)

    domains: list[str] = []
    domains += [_normalize_domain(d) for d in _split_csv_arg(args.domains)]
    if args.domains_file:
        with open(args.domains_file, "r", encoding="utf-8") as f:
            for line in f:
                d = _normalize_domain(line)
                if d:
                    domains.append(d)
    domains = sorted({d for d in domains if d})
    if not domains:
        print("No domains provided. Use --domains or --domains-file.", file=sys.stderr)
        return 2

    agent_tokens: list[str] = _split_csv_arg(args.agents)

    # Pull from Known Agents (optional but on by default, because it provides the latest list).
    knownagents_types = _split_csv_arg(args.knownagents_types)
    try:
        token_map = fetch_knownagents_user_agent_tokens(
            agent_types=knownagents_types,
            max_agents=max(1, int(args.max_agents)),
            timeout_s=float(args.timeout),
        )
    except Exception as e:  # noqa: BLE001
        token_map = {}
        print(f"Known Agents fetch failed: {type(e).__name__}: {e}", file=sys.stderr)

    # Merge tokens: explicit CLI tokens first (ensures inclusion even if Known Agents fails).
    merged_tokens = list(dict.fromkeys(agent_tokens + sorted(token_map.keys())))
    if not merged_tokens:
        print("No agent tokens found. Provide --agents or ensure Known Agents fetch works.", file=sys.stderr)
        return 2

    report: dict[str, Any] = {
        "path": args.path,
        "agents": merged_tokens,
        "domains": [],
    }

    rows: list[dict[str, Any]] = []

    for domain in domains:
        fetch = _http_get_robots(domain, timeout_s=float(args.timeout))
        groups = parse_robots_txt(fetch.text) if fetch.status_code and fetch.text else []
        domain_entry: dict[str, Any] = {
            "domain": domain,
            "robots": dataclasses.asdict(fetch),
            "results": [],
        }
        for token in merged_tokens:
            decision = decide_access(groups, token, args.path)
            result = {
                "agent": token,
                "classification": classify(decision),
                "allowed": decision.allowed,
                "rule_source": decision.rule_source,
                "matched_group_user_agents": decision.matched_group_uas,
                "matched_rule": dataclasses.asdict(decision.matched_rule) if decision.matched_rule else None,
                "knownagents": token_map.get(token),
            }
            domain_entry["results"].append(result)
            rows.append(
                {
                    "domain": domain,
                    "agent": token,
                    "classification": result["classification"],
                    "allowed": result["allowed"],
                    "rule_source": result["rule_source"],
                    "matched_rule_directive": (decision.matched_rule.directive if decision.matched_rule else ""),
                    "matched_rule_path": (decision.matched_rule.path if decision.matched_rule else ""),
                    "robots_url": fetch.final_url,
                    "robots_status": fetch.status_code,
                    "robots_error": fetch.error or "",
                }
            )
        report["domains"].append(domain_entry)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with open(args.out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "domain",
                "agent",
                "classification",
                "allowed",
                "rule_source",
                "matched_rule_directive",
                "matched_rule_path",
                "robots_url",
                "robots_status",
                "robots_error",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {args.out_json} and {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

