from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Any

import ai_robots_audit as audit


KEY_AI_AGENTS_DEFAULT = [
    "GPTBot",
    "ClaudeBot",
    "Google-Extended",
    "CCBot",
    "Amazonbot",
    "Applebot-Extended",
    "Bytespider",
    "FacebookBot",
    "meta-externalagent",
    "OAI-SearchBot",
    "Claude-SearchBot",
    "PerplexityBot",
    "YouBot",
    "ChatGPT-User",
    "Claude-User",
]


def _group_to_lines(g: audit.RobotsGroup) -> list[str]:
    lines: list[str] = []
    for ua in g.user_agents:
        lines.append(f"User-agent: {ua}")
    for r in g.rules:
        k = "Allow" if r.directive == "allow" else "Disallow"
        lines.append(f"{k}: {r.path}")
    return lines


def main() -> int:
    p = argparse.ArgumentParser(description="Summarize retailer robots.txt results.")
    p.add_argument("--report", default="report.json", help="Input JSON report from ai_robots_audit.py")
    p.add_argument("--out", default="retailers_ai_summary.md", help="Output markdown file")
    p.add_argument("--path", default="/", help="Path to evaluate (default: /)")
    p.add_argument(
        "--agents",
        default="",
        help="Comma-separated list of AI agent names to focus on. Empty = sensible defaults.",
    )
    args = p.parse_args()

    agents = [a.strip() for a in (args.agents or "").split(",") if a.strip()] or KEY_AI_AGENTS_DEFAULT

    with open(args.report, "r", encoding="utf-8") as f:
        report: dict[str, Any] = json.load(f)

    domains = report.get("domains", [])

    # Per-agent summary across all domains.
    counts_by_agent: dict[str, Counter[str]] = {a: Counter() for a in agents}
    failures = 0

    # Per-domain details we’ll highlight.
    domains_with_explicit_ai_rules: list[dict[str, Any]] = []
    most_restrictive: list[tuple[str, int]] = []

    for d in domains:
        domain = d.get("domain", "")
        robots = d.get("robots", {}) or {}
        status = int(robots.get("status_code") or 0)
        text = robots.get("text") or ""
        error = robots.get("error")

        if status <= 0 or not text:
            failures += 1
            for a in agents:
                counts_by_agent[a]["robots_not_fetched"] += 1
            continue

        groups = audit.parse_robots_txt(text)

        # Track explicit rules for key agents.
        explicit_blocks: dict[str, list[str]] = {}

        blocked_count = 0
        for a in agents:
            decision = audit.decide_access(groups, a, args.path)
            label = audit.classify(decision)
            counts_by_agent[a][label] += 1
            if not decision.allowed:
                blocked_count += 1

            # If there is an explicit block for this agent, capture the exact lines.
            if decision.rule_source == "explicit":
                # Find the groups that mention this agent by name.
                blocks: list[str] = []
                for g in groups:
                    exact, _ = audit._ua_matches(g.user_agents, a)  # type: ignore[attr-defined]
                    if exact:
                        blocks.extend(_group_to_lines(g))
                        blocks.append("")  # spacer
                if blocks:
                    explicit_blocks[a] = blocks[:-1] if blocks and blocks[-1] == "" else blocks

        most_restrictive.append((domain, blocked_count))
        if explicit_blocks:
            domains_with_explicit_ai_rules.append(
                {
                    "domain": domain,
                    "robots_url": robots.get("final_url"),
                    "explicit_blocks": explicit_blocks,
                }
            )

    most_restrictive.sort(key=lambda x: x[1], reverse=True)

    # Write markdown (plain language, no jargon).
    lines: list[str] = []
    lines.append("## Retailer robots.txt — AI agent analysis")
    lines.append("")
    lines.append(f"This report checks the path `{args.path}` on each retailer site.")
    lines.append("")
    lines.append("### What the labels mean")
    lines.append("")
    lines.append("- **Explicitly Allowed / Blocked**: the site names that bot directly (for example `User-agent: GPTBot`).")
    lines.append("- **General rule (Allowed/Blocked)**: the site uses `User-agent: *` (a rule for “all bots”), and the bot follows that.")
    lines.append("- **No matching rules (Allowed)**: there is no rule for that bot and no general rule, so it’s treated as allowed.")
    lines.append("- **robots.txt not fetched**: we couldn’t download the file (network error, blocked, or missing).")
    lines.append("")

    lines.append("### Summary by AI bot name")
    lines.append("")
    lines.append("| Bot name | Explicitly Blocked | Explicitly Allowed | General rule (Blocked) | General rule (Allowed) | No matching rules (Allowed) | robots.txt not fetched |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for a in agents:
        c = counts_by_agent[a]
        lines.append(
            "| "
            + " | ".join(
                [
                    a,
                    str(c.get("Explicitly Blocked", 0)),
                    str(c.get("Explicitly Allowed", 0)),
                    str(c.get("Wildcard Rule (Blocked)", 0)),
                    str(c.get("Wildcard Rule (Allowed)", 0)),
                    str(c.get("No Matching Rules (Implicitly Allowed)", 0)),
                    str(c.get("robots_not_fetched", 0)),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("### Most restrictive retailers (by how many of the listed AI bots are blocked)")
    lines.append("")
    lines.append("| Retailer domain | # bots blocked (out of listed bots) |")
    lines.append("|---|---:|")
    for domain, n in most_restrictive[:15]:
        lines.append(f"| {domain} | {n} |")
    lines.append("")

    lines.append("### Retailers that name AI bots directly (exact rules)")
    lines.append("")
    if not domains_with_explicit_ai_rules:
        lines.append("No retailer in this run named any of the listed AI bots directly.")
    else:
        for item in domains_with_explicit_ai_rules:
            lines.append(f"#### {item['domain']}")
            lines.append("")
            lines.append(f"robots.txt: `{item.get('robots_url')}`")
            lines.append("")
            for bot, block_lines in item["explicit_blocks"].items():
                lines.append(f"- **{bot}**")
                lines.append("")
                lines.append("```")
                lines.extend(block_lines)
                lines.append("```")
                lines.append("")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

