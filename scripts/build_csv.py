#!/usr/bin/env python3
"""
build_csv.py — turn approved registry rows into a HubSpot knowledge base import CSV.

The CSV is a *view* over the registry, never a hand-maintained artifact. If a value is
wrong in the CSV, fix it in Supabase or the vault draft and rebuild. Never edit the CSV
directly, and never fix a published article by hand in HubSpot, or the registry stops
being the truth.

Usage:
    python3 scripts/build_csv.py --out out/hubspot-import.csv
    python3 scripts/build_csv.py --category Products --dry-run

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in the environment or in .env.
Only rows at status = 'approved' are exported.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HELP_BASE = "https://help.oolio.com"
COLUMNS = [
    "URL", "TITLE", "CATEGORY", "SUBCATEGORY",
    "ARTICLE_BODY", "KEYWORDS", "META_DESCRIPTION", "SUBTITLE",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
CROSSLINK = re.compile(r"\[\[slug:([a-z0-9][a-z0-9-]*)\]\]")


# ----------------------------------------------------------------- environment

def load_env() -> None:
    env = REPO_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        sys.exit(f"{name} is not set. Add it to .env (see .env.example).")
    return value


# --------------------------------------------------------------------- fetch

def fetch_approved(category: str | None) -> list[dict]:
    """Read approved rows straight off PostgREST. No client library needed."""
    base = require("SUPABASE_URL").rstrip("/")
    key = require("SUPABASE_SERVICE_KEY")

    params = {
        "select": "slug,title,url,hubspot_category,hubspot_subcategory,"
                  "summary,keywords,vault_path,page_type",
        "status": "eq.approved",
        "order": "hubspot_category,hubspot_subcategory,title",
    }
    if category:
        params["hubspot_category"] = f"eq.{category}"

    url = f"{base}/rest/v1/docs_document?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    import json
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


# ---------------------------------------------------------------- conversion

def read_body(vault_path: str, vault_root: Path) -> str:
    """Read the drafted body from the vault, stripping YAML frontmatter."""
    path = vault_root / vault_path
    if not path.exists():
        raise FileNotFoundError(f"draft not found: {path}")
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    return text.lstrip("\n")


def resolve_crosslinks(text: str, known: set[str]) -> str:
    """[[slug:create-a-menu]] -> https://help.oolio.com/create-a-menu"""
    def repl(match: re.Match) -> str:
        slug = match.group(1)
        if slug not in known:
            raise ValueError(f"cross-link points at unknown slug: {slug}")
        return f"{HELP_BASE}/{slug}"
    return CROSSLINK.sub(repl, text)


def markdown_to_hubspot_html(markdown: str) -> str:
    """
    Convert to the constrained HTML subset HubSpot accepts.
    See context/html-subset.md — safe tags only, callouts as <p class="alert">.
    """
    try:
        import markdown as md  # type: ignore
    except ImportError:
        sys.exit(
            "The 'markdown' package is required.\n"
            "  pip3 install --break-system-packages markdown bleach"
        )
    try:
        import bleach  # type: ignore
    except ImportError:
        sys.exit(
            "The 'bleach' package is required.\n"
            "  pip3 install --break-system-packages markdown bleach"
        )

    html = md.markdown(markdown, extensions=["extra", "sane_lists"])

    allowed_tags = [
        "p", "a", "strong", "em", "ul", "ol", "li", "h2", "h3", "br", "span",
        # NOTE: table support is unverified against a real import.
        # See context/html-subset.md constraint 2 before relying on these.
        "table", "thead", "tbody", "tr", "th", "td",
    ]
    allowed_attrs = {
        "a": ["href", "target", "rel"],
        "p": ["class"],
        "span": ["class"],
    }
    cleaned = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    return f'<div id="post-body">{cleaned}</div>'


# ------------------------------------------------------------------- assemble

def build_row(record: dict, vault_root: Path, known_slugs: set[str]) -> dict:
    slug = record["slug"]
    body_md = read_body(record["vault_path"], vault_root)
    body_md = resolve_crosslinks(body_md, known_slugs)

    return {
        "URL": record.get("url") or f"{HELP_BASE}/{slug}",
        "TITLE": record["title"],
        "CATEGORY": record["hubspot_category"],
        "SUBCATEGORY": record["hubspot_subcategory"],
        "ARTICLE_BODY": markdown_to_hubspot_html(body_md),
        "KEYWORDS": record.get("keywords") or "",
        "META_DESCRIPTION": record.get("summary") or "",
        "SUBTITLE": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="out/hubspot-import.csv")
    parser.add_argument("--category", help="limit to one HubSpot CATEGORY")
    parser.add_argument("--vault", default=str(Path.home() / "my_brain"))
    parser.add_argument("--dry-run", action="store_true", help="report, write nothing")
    args = parser.parse_args()

    load_env()
    vault_root = Path(args.vault).expanduser()
    if not vault_root.exists():
        sys.exit(f"vault not found at {vault_root} — pass --vault")

    records = fetch_approved(args.category)
    if not records:
        print("No approved articles. Nothing to export.")
        return 0

    known_slugs = {r["slug"] for r in records if r.get("slug")}

    rows, failures = [], []
    for record in records:
        try:
            rows.append(build_row(record, vault_root, known_slugs))
        except (FileNotFoundError, ValueError, KeyError) as error:
            failures.append((record.get("slug") or record.get("title"), str(error)))

    for slug, error in failures:
        print(f"  SKIPPED  {slug}: {error}", file=sys.stderr)

    print(f"{len(rows)} article(s) ready, {len(failures)} skipped.")

    if args.dry_run:
        for row in rows:
            print(f"  {row['CATEGORY']} / {row['SUBCATEGORY']} — {row['TITLE']}")
        return 1 if failures else 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {out}")
    print(
        "\nBefore importing for real: confirm whether re-importing the same URL updates\n"
        "or duplicates. See context/html-subset.md, constraint 3. Test in a sandbox with\n"
        "two articles first."
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
