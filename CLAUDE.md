# Oolio Knowledge — operating manual

This repo holds **machinery, not content**. Scripts, agent definitions, extraction
rules and schema migrations live here. Article bodies never do.

If you are an agent working in this repo, read this file fully before acting.

---

## 1. Where things actually live

| Thing | Home | Notes |
|---|---|---|
| Article body, draft | `my_brain/10 Projects/Oolio/Help Centre/Drafts/<category>/<slug>.md` | Obsidian is the review surface |
| Article registry, the truth | Supabase project `oolio-tree` (`vcrajophxpoydfmronbi`), `docs_document` | one row per article, published or not |
| Feature ↔ article mapping | Supabase `docs_feature_document` | typed by `coverage` |
| Published article | HubSpot, `help.oolio.com` | **no API** — CSV import only |
| Product capability map ("the Tree") | Supabase `feature` / `featureGroup` / `products` | 868 features, 93 groups, 13 products |
| Source code | `~/Documents/GitHub/<repo>` | read-only, never modify |
| Voice, page formulas, IA | `my_brain/10 Projects/Oolio/Oolio Tree/HubSpot Wiki Proposal.md` | **canonical — read it, do not copy it here** |
| Tree structuring rules | `my_brain/10 Projects/Oolio/Oolio Tree/Tree Standard.md` | contract for anything touching the Tree |

Claude Code only sees its working directory. Start sessions with the other roots attached:

```
cd ~/Documents/GitHub/oolio-knowledge
claude --add-dir ~/Documents/GitHub/products --add-dir ~/my_brain
```

**Never create a `wiki/` or `drafts/` folder in this repo.** A second home for bodies
will fork from the vault within a week and then nobody knows which draft is current.

---

## 2. Hard rules

1. **Never assume one repository contains the complete workflow.** A customer-visible
   job routinely spans a web app, a Go service and an SDK. Check before concluding.

2. **State uncertainty. Do not resolve it silently.** If behaviour cannot be proven
   from code, the Tree, or a cited source, say so and mark the claim `unproven`. A
   confidently wrong article is worse than a missing one, because the HubSpot support
   agent will repeat it to a customer.

3. **Every behavioural claim carries a citation** — `file:line`, a Tree `feature.id`,
   or a source URL. Claims without one do not ship.

4. **Never overwrite human-written content without review.** Propose a diff; let a
   human accept it.

5. **Code tells you what, never why.** It gives you options, states, error strings,
   permissions and limits. It cannot tell you what a venue manager is trying to do at
   6pm on a Friday. Product intent comes from the Tree, the Product Domains in the
   vault, and Jira — not from reading components.

6. **Annotate, do not delete.** Superseded text gets struck through and left visible
   with the correction beside it. This applies to drafts and vault pages alike.

7. **Dated engineering plans are not behaviour.** `docs/superpowers/plans/*` in the
   products repo records what someone intended to build on a date. Useful for release
   notes, actively dangerous as a source of truth for how the product works today.

---

## 3. Where the work stands (August 2026)

- 868 features in the Tree. **592 live** (released, beta, pilot).
- **128 live features carry a help link. 464 do not.**
- 161 articles in the help centre, across 7 sections.
- `docs_feature_document` and `docs_feature_override` exist and are **empty**. The
  graph is modelled but unpopulated — this is a population job, not a design job.
- `feature.link` is a legacy free-text URL column doing the same job worse. Migrate it
  into `docs_feature_document` and stop writing to it.
- All 161 `docs_document.summary` values are null.

**The live problem.** Back Office 2.0 becomes the default for every user on
**17 August 2026**, and that date does not move. Of the 38 articles under
Back Office / Products:

- roughly 17 document the **original** app (the `…-oolio-help-center` URLs) and become
  wrong instructions on that date
- roughly 7 are duplicate pairs — the 2.0 set was written twice, once as
  "(Back Office 2.0)" and once as "(in Back Office 2.0)"
- at least 4 should never have been published: a page whose URL is
  `do-not-publish-or-archive-.-`, an "Internal Guide Only" page, two with `[draft]` in
  the public title, and one whose URL is the unreplaced template placeholder
  `whatquestionisyourarticleanswering`

Triaging those 38 is the first pass. Drafting new articles comes after.

---

## 4. Description coverage by product

Uneven, and it determines how much raw material a section gives you.

| Product | Live | Linked | Gap | Have descriptions |
|---|---|---|---|---|
| Online Ordering | 92 | 8 | 84 | 100% |
| POS | 109 | 41 | 68 | 18% |
| Reporting | 83 | 17 | 66 | 100% |
| Customers | 79 | 16 | 63 | 100% |
| Products | 65 | 23 | 42 | 100% |
| mPOS & Tap to Pay | 47 | 8 | 39 | 6% |
| KDS | 43 | 5 | 38 | 21% |
| Kiosk | 36 | 2 | 34 | 24% |
| Integrations | 28 | 5 | 23 | 12% |

Inventory has 78 fully-described features and **nothing live yet** — documentation that
can be written ahead of launch rather than behind it.

---

## 5. The pipeline

```
repos ──► code facts ──┐
                       ├──► draft (vault) ──► registry (Supabase) ──► CSV ──► HubSpot
Tree + Product Domains ┘                            ▲
                                                    │
                              existing 161 articles ┘  (reconcile branch)
```

Two branches, not one. **Reconcile** handles what already exists; **draft** handles
what does not. The first pass is entirely reconcile.

---

## 6. Article anatomy

Frontmatter on every draft file:

```yaml
---
doc_id: <uuid, matches docs_document.id>
slug: create-a-product-group        # assigned up front, before publication
title: Create a product group
page_type: task                     # task | hub | track | reference | fix | concept | release | known_issue
category: Products                  # HubSpot CATEGORY
subcategory: Product setup          # HubSpot SUBCATEGORY
status: drafting                    # planned | drafting | in_review | approved | published | retired
features: [<feature.id>, ...]       # Tree features this covers; empty is valid
sources:
  - products@web/app/routes/_app.$orgId.products._index.tsx:24
  - tree:feature/<uuid>
---
```

### The lifecycle, and who moves it

```
planned ──► drafting ──► in_review ──► approved ──► published
                            │                          │
                            └──► (sent back) ◄─────── retired
```

| Status | Set by | Means |
|---|---|---|
| `planned` | whoever identifies the gap | needed, nothing written |
| `drafting` | `article-writer` | being written in the vault |
| `in_review` | `article-writer`, on handing over | with `accuracy-reviewer` or a human |
| `approved` | **a human, never an agent** | passed review, eligible for export |
| `published` | `build_csv.py` after a confirmed import | live in HubSpot, `url` populated |
| `retired` | `article-reconciler` verdict, human-confirmed | withdrawn; row kept for history |

**`approved` is the gate, and it is the one status no agent may set.** Only rows at
`status = 'approved'` are exported to the CSV — an article that never reaches it never
reaches a customer, and an article that reaches it without a human is exactly the
failure hard rule 4 exists to prevent. `accuracy-reviewer` returning `verdict: pass`
makes a draft *eligible* for `approved`; it does not confer it.

Two check constraints enforce the tail of this in the database: a row at `approved` or
`published` must carry `slug`, both HubSpot category columns and a non-empty `summary`;
a row at `published` must have a `url`. Attempting to skip a step fails the write rather
than shipping a half-populated article.

`page_type` carries the how-to/troubleshooting distinction: **task** is the how-to,
**fix** is the troubleshooting guide. They do not get their own folders — a menus
troubleshooting guide sits under the Menus category with `page_type: fix`.

A document with an empty `features` list is legitimate. Hubs, troubleshooting and
concept pages often map to no single Tree node. Coverage reporting must not count these
as orphans.

The eight page-type formulas are §10 of the HubSpot Wiki Proposal. **Read them from the
vault.** They are not reproduced here, deliberately — one copy, one truth.

---

## 7. Publishing constraints

HubSpot's knowledge base has no API. Publication is a CSV import with exactly eight
columns:

```
URL, TITLE, CATEGORY, SUBCATEGORY, ARTICLE_BODY, KEYWORDS, META_DESCRIPTION, SUBTITLE
```

Consequences that shape drafting, in `context/html-subset.md`:

- `ARTICLE_BODY` is **HTML, not Markdown**, and a narrow subset of it
- only **two** levels of hierarchy exist — the proposal's three-tier IA has to collapse
- whether re-import updates or duplicates is **unverified**. Until it is confirmed,
  treat every import as potentially one-way and do not rely on being able to correct a
  published article by re-importing it.

---

## 8. Agents

| Agent | Does | Never does |
|---|---|---|
| `code-researcher` | Extracts verifiable facts from repos with `file:line` citations | Writes prose, infers intent |
| `article-reconciler` | Judges an existing article against code + Tree | Rewrites without a verdict first |
| `article-writer` | Drafts to the §10 formulas in house voice | Makes uncited behavioural claims |
| `accuracy-reviewer` | Tries to refute every claim | Softens an unproven claim instead of flagging it |

Run them in that order. The reviewer is adversarial by design — its job is to fail
drafts, not to bless them.
