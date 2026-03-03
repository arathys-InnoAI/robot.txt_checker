# AI Robots.txt Drill-Down Audit

This repo contains a small script that:

- Pulls a current list of known AI agents from `knownagents.com/agents`
- Extracts canonical `User-agent` tokens (as used in robots.txt examples)
- Fetches `robots.txt` for each target domain
- Classifies each agent as:
  - **Explicitly Allowed**
  - **Explicitly Blocked**
  - **Wildcard Rule (Allowed/Blocked)**
  - **No Matching Rules (Implicitly Allowed)**

## Setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Run

Example (audit a few domains against a few agents):

```bash
python ai_robots_audit.py --domains example.com,openai.com --agents GPTBot,ClaudeBot,Google-Extended,CCBot
```

Example (pull agents from Known Agents and audit them):

```bash
python ai_robots_audit.py --domains example.com --knownagents-types ai-data-scraper,ai-search-crawler --max-agents 50
```

Outputs:

- `report.json` (default)
- `report.csv` (default)

## Notes on robots.txt logic

- The script evaluates access for path `/` by default (change with `--path`).
- If an agent has an explicit `User-agent: <token>` group, that group is used.
- Otherwise, if a wildcard `User-agent: *` group exists, that is used.
- Otherwise, it’s treated as **implicitly allowed**.

