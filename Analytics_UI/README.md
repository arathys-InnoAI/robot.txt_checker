# Robots.txt Audit — Analytics UI

A simple in-browser analytics page for the CSV reports produced by `ai_robots_audit.py`.

## How to use

1. Open `index.html` in your browser (double-click or drag into Chrome/Edge/Firefox).
2. Click **Upload CSV** and choose a report file from `../OUTPUT/` (e.g. `robots_audit_YYYYMMDD_HHMMSS.csv`).
3. Use the filters and tables/charts to explore the data.

## Features

- **Upload CSV** — Use any audit CSV from the script (same column names).
- **Filter by domains** — Multi-select domains to see only those rows (and which agents they apply to).
- **Filter by agents** — Multi-select agents to see which domains allow or block them.
- **Filter by classification** — Explicitly Allowed, Explicitly Blocked, Wildcard (Allowed/Blocked), No Matching Rules.
- **Filter by allowed** — Show only rows where the agent is allowed (true) or blocked (false).
- **Summary cards** — Counts of filtered rows, unique domains, unique agents, allowed vs blocked.
- **Charts** — Bar charts: “By agent” (allowed/blocked per agent) and “By domain” (allowed/blocked per domain).
- **Data table** — Sortable view of filtered rows (domain, agent, classification, allowed, allow_rules, disallow_rules, etc.). First 500 rows shown; summary shows total.

No server or install needed: everything runs in the browser. Data never leaves your machine.
