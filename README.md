## AI robots.txt checker

This project helps you see how websites treat AI bots (like `GPTBot`, `ClaudeBot`, `Google-Extended`, `CCBot`, etc.) in their `robots.txt` file.

You can:

- **Scan many domains at once** and fetch their `robots.txt`.
- **Classify rules** for each AI bot:
  - **Explicitly Allowed**
  - **Explicitly Blocked**
  - **General rule (Allowed/Blocked)** via `User-agent: *`
  - **No Matching Rules (Implicitly Allowed)**
- **Create a human-readable summary** for decision makers.

---

## 1. Setup

From the project folder:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Key files

- `ai_robots_audit.py` – core script that:
  - gets AI bot names (optionally from `knownagents.com/agents`)
  - fetches `robots.txt` for each domain
  - decides if each bot is allowed or blocked
  - writes detailed JSON and CSV reports
- `usretailers.txt` – example list of US retailer domains (one per line).
- `domains.txt` / `domains.csv` – example domain lists you can replace with your own.
- `workflow.md` – step‑by‑step guide for running retailer checks and reading the results.
- `summarize_retailers.py` – turns a JSON report into a plain‑English markdown summary.

---

## 3. Quick start: audit a few domains

Simple one‑off run:

```bash
python ai_robots_audit.py ^
  --domains example.com,openai.com ^
  --agents GPTBot,ClaudeBot,Google-Extended,CCBot ^
  --output-dir OUTPUT
```

This writes:

- a JSON report like `OUTPUT/robots_audit_YYYYMMDD_HHMMSS.json`
- a CSV report like `OUTPUT/robots_audit_YYYYMMDD_HHMMSS.csv`
and shows a short summary in the terminal:

- how many domains were given
- how many `robots.txt` files were fetched and parsed as text
- how many responses looked like HTML (skipped)
- how many were empty or returned HTTP errors

---

## 4. Deep dive: US retailers workflow

1. **Prepare the domain list**
   - Edit `usretailers.txt` if you want to add or remove domains.

2. **Run the retailer audit**

   ```bash
   python ai_robots_audit.py ^
     --domains-file usretailers.txt ^
     --agents GPTBot,ClaudeBot,Google-Extended,CCBot,Amazonbot,Applebot-Extended,Bytespider,FacebookBot,meta-externalagent,OAI-SearchBot,Claude-SearchBot,PerplexityBot,YouBot,ChatGPT-User,Claude-User ^
     --knownagents-types ai-data-scraper,ai-search-crawler ^
     --max-agents 200 ^
     --output-dir OUTPUT
   ```

   In the terminal you will also see a summary line with:

   - total domains
   - how many `robots.txt` files were parsed as text
   - how many looked like HTML and were skipped
   - how many were missing or had HTTP errors

3. **Generate a human‑friendly summary**

   ```bash
   python summarize_retailers.py --report retailers_report.json --out retailers_ai_summary.md
   ```

4. **Read the summary**
   - Open `retailers_ai_summary.md`.
   - It explains, in simple language:
     - which bots are blocked or allowed
     - which retailers are most restrictive
     - any sites that mention specific AI bots by name.

For a slower, more detailed explanation, open `workflow.md`.

---

## 5. How the robots.txt logic works

- The tool checks one path at a time (default: `/`, change with `--path`).
- If a `User-agent: <bot name>` block exists, that wins.
- If there is no bot‑specific block, but there is a `User-agent: *` block, that is used.
- If there is no matching block at all, the bot is treated as **allowed**.
- If multiple rules match, the **most specific path** wins (longest match, or more detailed pattern).
- The JSON report also stores:
  - **all user-agent names** mentioned in the file
  - the rule that applies to `User-agent: *` (all bots)
  - the default rule that applies to **any bot that is not named** in the file.

---

## 6. Mode: use the site’s own User-agent list

If you do **not** want to specify bots yourself, you can tell the tool to use whatever the site wrote inside `robots.txt`.

This will create CSV rows for:

- every `User-agent:` name found in that domain’s `robots.txt` (including `*` if present)
- one extra row called **`DEFAULT/OTHER`** (meaning “any bot not named in this file”)

Example:

```bash
python ai_robots_audit.py ^
  --domains openai.com ^
  --agents-mode robots ^
  --no-knownagents ^
  --output-dir OUTPUT
```

