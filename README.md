# AI robots.txt checker

This project audits how websites treat AI bots (e.g. GPTBot, ClaudeBot, Google-Extended, CCBot) in their `robots.txt` file. You can scan many domains, classify allow/block rules per agent, and get JSON/CSV reports plus an optional analytics UI.

---

## 1. Setup

From the project folder:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Check that it runs:**

```powershell
python ai_robots_audit.py --help
```

---

## 2. Command reference (all options)

Every way to run the script uses this executable:

```text
python ai_robots_audit.py [options]
```

### Domains (choose one or both)

| Option | What it does |
|--------|----------------|
| `--domains DOMAINS` | Comma-separated list of domains (no `https://`). Example: `--domains example.com,openai.com,target.com` |
| `--domains-file FILE` | Text file with one domain per line (blank lines and `#` comments ignored). Lines can be plain `domain.com` or full URLs; the script strips to the host. Example: `--domains-file usretailers.txt` |

You can use both; domains from the file and from `--domains` are merged and de-duplicated.

### Which agents to audit

| Option | What it does |
|--------|----------------|
| `--agents AGENTS` | Comma-separated list of bot names (User-agent tokens). Example: `--agents GPTBot,ClaudeBot,Google-Extended,CCBot` |
| `--agents-mode MODE` | Controls **which agents** appear in the CSV. One of: `specified` (default), `robots`, `robots+specified`. See “Ways to run” below. |
| `--knownagents-types TYPES` | When fetching from knownagents.com, limit to these type slugs (comma-separated). Example: `--knownagents-types ai-data-scraper,ai-search-crawler`. Empty = all types. |
| `--no-knownagents` | Do **not** fetch extra agents from knownagents.com. Faster; use with `--agents-mode robots` when you only care about each site’s own User-agent list. |
| `--max-agents N` | When using knownagents.com, stop after collecting this many agent slugs (default: 50). Example: `--max-agents 200` |

### What gets evaluated

| Option | What it does |
|--------|----------------|
| `--path PATH` | URL path to evaluate against Allow/Disallow rules (default: `/`). Example: `--path /api/` |

### Output

| Option | What it does |
|--------|----------------|
| `--output-dir DIR` | Folder where JSON and CSV are written (default: `OUTPUT`). Created if missing. |
| `--out-json NAME` | JSON filename. Default `report.json` becomes `robots_audit_YYYYMMDD_HHMMSS.json` inside `--output-dir`. |
| `--out-csv NAME` | CSV filename. Default `report.csv` becomes `robots_audit_YYYYMMDD_HHMMSS.csv` inside `--output-dir`. |

### Network

| Option | What it does |
|--------|----------------|
| `--timeout SECONDS` | HTTP timeout in seconds for each request (default: 15.0). |

---

## 3. Ways to run (with examples)

### A. Quick test: a few domains, a few agents

**What it does:** Fetches `robots.txt` for each domain, checks the listed agents, writes one JSON and one CSV in `OUTPUT/` with timestamped names.

```powershell
python ai_robots_audit.py --domains example.com,openai.com,anthropic.com --agents GPTBot,ClaudeBot,Google-Extended,CCBot --output-dir OUTPUT
```

- Uses your **specified agents** only (no knownagents.com fetch unless you add types).
- Output: `OUTPUT/robots_audit_YYYYMMDD_HHMMSS.json` and `.csv`.

---

### B. Many domains from a file, specified agents only

**What it does:** Reads domains from a file, audits each against the agents you list. Good for retailer or custom domain lists.

```powershell
python ai_robots_audit.py --domains-file usretailers.txt --agents GPTBot,ClaudeBot,Google-Extended,CCBot,Amazonbot,OAI-SearchBot,Claude-SearchBot,PerplexityBot,ChatGPT-User,Claude-User --output-dir OUTPUT
```

- **Domains:** from `usretailers.txt` (one per line).
- **Agents:** only those in `--agents`.
- No knownagents.com call.

---

### C. Many domains + extra agents from Known Agents (with agent types)

**What it does:** Same as B, but also fetches more agents from knownagents.com by type. CSV will include an `agent_type` column (e.g. “AI Data Scraper”) when the agent is known.

```powershell
python ai_robots_audit.py --domains-file usretailers.txt --agents GPTBot,ClaudeBot,Google-Extended,CCBot --knownagents-types ai-data-scraper,ai-search-crawler --max-agents 200 --output-dir OUTPUT
```

- **Domains:** from `usretailers.txt`.
- **Agents:** your list **plus** up to 200 agents from knownagents.com (types `ai-data-scraper` and `ai-search-crawler`).
- Slower due to knownagents.com requests; use when you want broad coverage and agent types.

---

### D. Use each site’s own User-agent list (no agent list needed)

**What it does:** For each domain, parses its `robots.txt` and outputs one row per **User-agent** name found there, plus one row for **DEFAULT/OTHER** (any bot not named). No need to pass `--agents`.

```powershell
python ai_robots_audit.py --domains-file usretailers.txt --agents-mode robots --no-knownagents --output-dir OUTPUT
```

- **Domains:** from `usretailers.txt`.
- **Agents:** taken from each site’s robots.txt (e.g. `*`, `Googlebot`, `GPTBot`, …) plus `DEFAULT/OTHER`.
- `--no-knownagents` keeps the run fast.
- Use when you want “what does this site’s robots.txt say about each bot it mentions?”

---

### E. Combine site’s agents + your list + Known Agents

**What it does:** CSV rows include every agent that appears in any site’s robots.txt, every agent you pass with `--agents`, and (if you don’t use `--no-knownagents`) agents from knownagents.com; plus `DEFAULT/OTHER`.

```powershell
python ai_robots_audit.py --domains-file usretailers.txt --agents-mode robots+specified --agents GPTBot,ClaudeBot --knownagents-types ai-data-scraper --max-agents 100 --output-dir OUTPUT
```

- **Domains:** from file.
- **Agents:** union of (robots.txt names + your list + knownagents.com, up to 100) plus `DEFAULT/OTHER`.

---

### F. Custom output folder and filenames

**What it does:** Puts reports in a folder you choose; you can fix the filename (no timestamp) if you want.

```powershell
python ai_robots_audit.py --domains example.com --agents GPTBot --output-dir MyReports --out-json my_audit.json --out-csv my_audit.csv
```

- Writes `MyReports/my_audit.json` and `MyReports/my_audit.csv`.
- If you omit `--out-json` / `--out-csv`, default names are used and **then** a timestamp is added when the default is `report.json` / `report.csv`.

---

### G. Check a specific path (e.g. /api/)

**What it does:** Same as any run above, but the allow/block decision is for the given path instead of `/`.

```powershell
python ai_robots_audit.py --domains api.example.com --agents GPTBot --path /api/ --output-dir OUTPUT
```

- Classification (allowed/blocked) is for `https://api.example.com/api/` (and prefixes), not for `/`.

---

### H. Longer timeout (slow or distant servers)

**What it does:** Increases how long the script waits for each `robots.txt` (and knownagents.com) request.

```powershell
python ai_robots_audit.py --domains-file slow-sites.txt --agents GPTBot --timeout 30 --output-dir OUTPUT
```

- 30 seconds per HTTP request instead of 15.

---

## 4. What the script prints

After every run you see a short summary, for example:

```text
Checking robots.txt for 54 domain(s)...
  [1/54] 7-eleven.com
  ...
Wrote OUTPUT/robots_audit_20260305_140000.json and OUTPUT/robots_audit_20260305_140000.csv

Run summary:
- Domains given: 54
- robots.txt fetched and parsed as text: 52
- robots.txt returned HTML (skipped parsing): 1
- robots.txt empty body: 0
- robots.txt missing or HTTP error: 1
```

- **Domains given:** Total domains after merging `--domains` and `--domains-file`.
- **Fetched and parsed as text:** Successfully downloaded and treated as plain-text robots.txt (not HTML).
- **Returned HTML:** Response looked like an HTML page; not parsed as rules.
- **Empty body:** No content.
- **Missing or HTTP error:** Network error, 403, 404, 5xx, etc.

---

## 5. Output files (CSV columns)

Reports are written under `--output-dir` (default `OUTPUT/`).

**CSV columns:**

| Column | Meaning |
|--------|--------|
| `domain` | The site (e.g. `amazon.com`). |
| `agent` | Bot name (e.g. `GPTBot`, `*`, `DEFAULT/OTHER`). |
| `classification` | Explicitly Allowed, Explicitly Blocked, Wildcard Rule (Allowed/Blocked), or No Matching Rules (Implicitly Allowed). |
| `allowed` | `True` or `False` for the evaluated path. |
| `rule_source` | `explicit`, `wildcard`, or `none`. |
| `matched_rule_directive` | `allow` or `disallow` for the rule that decided the result. |
| `matched_rule_path` | Path/pattern of that rule. |
| `allow_rules` | All Allow paths for this agent, joined with ` \| `. |
| `disallow_rules` | All Disallow paths for this agent, joined with ` \| `. |
| `agent_type` | Type from knownagents.com if available (e.g. AI Data Scraper); empty otherwise. |
| `robots_url` | URL that was fetched for robots.txt. |
| `robots_status` | HTTP status (200, 403, 404, …). |
| `robots_error` | Network/error message if fetch failed. |
| `robots_parsed` | Whether the response was parsed as text robots.txt. |
| `robots_looks_html` | Whether the response looked like HTML (and was skipped). |

**JSON:** Same data in a nested structure (per-domain, per-agent), plus metadata (path evaluated, agents_mode, generated_at, output file paths).

---

## 6. How allow/block is decided

- The script evaluates **one path** per run (default `/`, overridden by `--path`).
- If the site has a **User-agent:** block that matches the bot by name, that block’s rules are used (**explicit**).
- If there is no matching name but there is a **User-agent: *** block, that block is used (**wildcard**).
- If there is no matching block at all, the bot is treated as **allowed** (**no matching rules**).
- When several rules match the path, the **most specific** (longest path match) wins; Allow wins over Disallow on a tie.

---

## 7. Other files in the project

| File / folder | Purpose |
|----------------|--------|
| `usretailers.txt` | Example domain list (US retailers); edit and use with `--domains-file`. |
| `domains.txt`, `domains.csv` | Other example domain lists. |
| `workflow.md` | Step-by-step narrative for running audits and reading results. |
| `summarize_retailers.py` | Builds a markdown summary from a JSON report (e.g. for the “specified agents” workflow). |
| `Analytics_UI/` | Browser UI to upload a CSV and filter/visualise by domain, agent, allowed, etc. Open `Analytics_UI/index.html` in a browser. |

---

## 8. Line continuation (PowerShell vs CMD vs Bash)

- **PowerShell:** use a **backtick** `` ` `` at the end of a line to continue the command on the next line.
- **CMD:** use **caret** `^` at the end of a line.
- **Bash / sh:** use backslash `\` at the end of a line.

Single-line commands work in all shells; use continuation only when you want a readable multi-line command.
