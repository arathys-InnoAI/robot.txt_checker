## Goal

Use `robots.txt` to see what each retailer site says about AI bots like **GPTBot**, **ClaudeBot**, **Google-Extended**, and **CCBot**.

You will get:

- A full results file in **JSON** and **CSV**
- A human‑readable **summary markdown** report

## What the script checks

Every website can publish a file at:

- `https://<domain>/robots.txt`

That file usually contains blocks like:

```
User-agent: GPTBot
Disallow: /
```

Meaning: “GPTBot should not visit any pages on this site.”

Sometimes a site uses a general rule:

```
User-agent: *
Disallow: /
```

Meaning: “All bots should not visit.”

## Inputs

- `usretailers.txt`: one retailer domain per line.
  - It can be either `target.com` or a full URL like `https://target.com/`.

## Step 1 — Install the Python package we use

```bash
python -m pip install -r requirements.txt
```

## Step 2 — Run the retailer audit

This command:

- reads domains from `usretailers.txt`
- checks each site’s `robots.txt`
- focuses on common AI crawler names

```bash
python ai_robots_audit.py ^
  --domains-file usretailers.txt ^
  --agents GPTBot,ClaudeBot,Google-Extended,CCBot,Amazonbot,Applebot-Extended,Bytespider,FacebookBot,meta-externalagent,OAI-SearchBot,Claude-SearchBot,PerplexityBot,YouBot,ChatGPT-User,Claude-User ^
  --knownagents-types ai-data-scraper,ai-search-crawler ^
  --max-agents 200 ^
  --out-json retailers_report.json ^
  --out-csv retailers_report.csv
```

## Step 3 — Create a plain-English summary report

This command reads `retailers_report.json` and writes `retailers_ai_summary.md`.

```bash
python summarize_retailers.py --report retailers_report.json --out retailers_ai_summary.md
```

## How to read the results

In the summary report:

- **Explicitly Blocked** means the site names the bot directly and blocks it.
- **Explicitly Allowed** means the site names the bot directly and allows it.
- **General rule (Blocked/Allowed)** means the site does not name the bot, but uses a general rule for all bots.
- **No matching rules (Allowed)** means the file has no rule for that bot, so it’s treated as allowed.

