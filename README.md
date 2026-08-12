# oolio-knowledge

Machinery for building and maintaining the Oolio help centre. Agents, scripts, schema
and rules — **no article content**.

Bodies live in the `my_brain` vault. Truth lives in Supabase. Published lives in HubSpot.
This repo is what moves things between them.

## Setup

```bash
cp .env.example .env          # then fill in the two Supabase keys
pip3 install --break-system-packages markdown bleach
```

Start Claude Code with the code and the vault attached, or agents can only see this repo:

```bash
cd ~/Documents/GitHub/oolio-knowledge
claude --add-dir ~/Documents/GitHub/products --add-dir ~/my_brain
```

Read `CLAUDE.md` — it is the operating manual and agents are expected to follow it.

## Layout

```
CLAUDE.md                  operating manual — source-of-truth map, hard rules, state
.mcp.json                  Supabase MCP wired to the oolio-tree project
.claude/agents/            code-researcher, article-reconciler, article-writer,
                           accuracy-reviewer
context/
  html-subset.md           what survives the CSV import; the publishing contract
  registry.md              the Supabase schema and the queries you will actually run
  sources.md               pointers to canonical standards — read, never copy
migrations/
  001_docs_document_lifecycle.sql
scripts/
  build_csv.py             approved registry rows → HubSpot import CSV
```

## First run

1. **Review and apply the migration.** `migrations/001_docs_document_lifecycle.sql` adds
   the draft lifecycle to `docs_document`. Read it before running it — it makes `url`
   nullable and adds check constraints.

2. **Backfill the 161 existing articles.** Fetch each live page, populate `summary`,
   `body_html` and `app_version`. Every summary is null today, and `app_version` is what
   makes the Products triage possible.

3. **Triage the 38 Back Office / Products articles** with `article-reconciler`. Roughly
   17 describe the superseded app, about 7 are duplicate pairs, and at least 4 should
   never have been published. Back Office 2.0 becomes the default on **17 August 2026**,
   which is when the legacy articles become actively wrong.

4. **Verify the CSV round-trip** before drafting anything new. Import two articles into a
   sandbox, edit one, re-import, and find out whether HubSpot updates or duplicates. If
   it duplicates, the pipeline is one-way and that changes the plan. See
   `context/html-subset.md`, constraint 3.

Only then start drafting.

## Rules worth repeating

- Never create a `wiki/` or `drafts/` folder here. Bodies live in the vault, one copy.
- Every behavioural claim carries a citation. Uncited claims do not ship.
- Say when you are unsure. The HubSpot support agent reads these articles to customers —
  a confident guess reaches a real person.
- Annotate, never delete. Superseded text is struck through, not removed.
