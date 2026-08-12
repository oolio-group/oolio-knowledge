# Canonical sources — read these, do not copy them

Everything below lives somewhere else and stays there. This file exists so agents can
find it, not so the content can be duplicated into this repo. Two copies of a standard
means two standards within a month.

## The standards, in the vault

| What | Path | Read it when |
|---|---|---|
| Voice, page rules, accessibility | `my_brain/10 Projects/Oolio/Oolio Tree/HubSpot Wiki Proposal.md` §9 | before writing any article |
| The eight page-type formulas | same file, §10 | before writing any article |
| Sizing and priority formulas | same file, §11 | deciding if a feature earns an article, what to write first |
| IA and governance rules | same file, §12 | assigning category and subcategory |
| The Article Register | same file, §13 | understanding what the registry is meant to become |
| The council's changes | `HubSpot Wiki Proposal VPC Decision Log.md` | before reopening a settled decision |
| Tree structuring contract | `Tree Standard.md` | before changing anything in the Tree |
| The four-stage section process | `Sections/00 Section Model.md` | working through a new product area |
| Products capability audit | `Products Feature Audit.md` | Products-specific work |
| Per-section detail | `Sections/01 POS.md` … `13 Reservations.md` | working that section |

## The internal knowledge wiki

`my_brain/30 Knowledge/Product Domains/` — Back Office, Customer Engagement, Insights,
Integrations, Inventory, Legacy Migration, Menu and Pricing, Ordering, POS, Payments,
Platform Admin.

This is the *reasoning* brain: distilled, cross-linked, provenance-carrying. It is where
**product intent** comes from — what a capability is for, who uses it, why it exists.
Code cannot tell you any of that.

Do not write help centre articles into it. Different genre, different reader, and mixing
them degrades the domain wikis for every other purpose.

## The code

| Repo | Path | Serves |
|---|---|---|
| `products` | `~/Documents/GitHub/products` | Back Office 2.0 — Menus, Price Lists, Products, Image Library, Variants, Option Groups, Schedule |

`product_repo_map` in Supabase has 38 repo↔product mappings. Clone lazily — only what
the current section needs. `products` alone is 206 MB.

High-value files in `products`:

- `web/app/routes/` — 43 route files, the ground-truth page inventory
- `web/app/constants/message.ts` — human-written customer-facing tooltip prose
- `web/app/constants/permissions.ts` — four permissions, authoritative
- `docs/specs/`, `docs/adr/` — small, genuine *why*
- `docs/superpowers/plans/` — **dated intent, not behaviour**

## The live help centre

`help.oolio.com` — 161 articles, mirrored in `docs_document`. Sections today are Back
Office, Front of House, Reporting, Apps & Devices, Integrations, Technical & Support and
Legacy (Intercom), which do **not** match the proposal's IA. Re-homing all 161 is part
of this work, not just adding new ones.

## Jira

Products App work runs in `PAPP` (initiative INI-176). Discovery ideas in `OHSI`. The
team ships into six projects — PAPP, OOM, OPC, OK, OC, EDU — because product, menu and
price data is the spine that POS, Kiosk, Online Store and Orders hang off.

Useful for *why* and for what is coming. Not a source of truth for current behaviour.
