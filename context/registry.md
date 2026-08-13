# The registry — Supabase `oolio-tree`

Project ref `vcrajophxpoydfmronbi`, region `ap-southeast-2`, org Oolio.

This database holds two things that were built separately and are about to become one:
the **Tree** (what Oolio ships) and the **doc graph** (what is documented). The join
between them exists and is empty. Filling it is the point.

## The Tree

| Table | Rows | What |
|---|---|---|
| `products` | 13 | Top level — POS, Products, Reporting, Kiosk, … |
| `featureGroup` | 93 | Groups within a product, `productId` FK |
| `feature` | 868 | The capabilities, `featureGroupId` FK, self-referencing `parentFeatureId` for sub-features |

`feature` columns worth knowing: `name`, `description`, `status`
(`released` / `building` / `roadmap` / `beta` / `pilot`), `link`, `eta`, `fiscalYear`.

**`feature.link` is legacy.** It is a single free-text URL doing the job that
`docs_feature_document` does properly. 128 features carry one. Migrate them into the
join table and stop writing to it — but do not drop the column until the doc graph app
has been checked, since it may still read it.

## The doc graph

| Table | Rows | What |
|---|---|---|
| `docs_document` | 161 | One row per help article |
| `docs_feature_document` | **0** | feature ↔ document, with `coverage` |
| `docs_feature_override` | **0** | manual per-feature documentation status |

`docs_feature_document.coverage` — `primary` / `supporting` / `partial` / `stale`.
`docs_feature_override.doc_status` — `documented` / `partial` / `outdated` /
`undocumented` / `not_required`.

`not_required` matters. Not every feature earns an article; §11.1 of the proposal has
the test. Marking a feature `not_required` is a real decision, not a cop-out, and it
stops coverage metrics from chasing 100% of something that should never reach 100%.

## What `docs_document` is missing

Today it assumes every article is live: `url` is NOT NULL and unique, and there is no
status. A draft sitting in the vault cannot be represented, which breaks the whole
draft-then-publish model.

`migrations/001_docs_document_lifecycle.sql` adds:

| Column | Why |
|---|---|
| `status` | `planned` → `drafting` → `in_review` → `approved` → `published` → `retired` |
| `slug` | assigned before publication; solves cross-linking; the stable identity |
| `vault_path` | where the draft body lives in my_brain |
| `page_type` | the §10 formula this article follows |
| `hubspot_category` / `hubspot_subcategory` | the two CSV columns, separate from the legacy `section` / `category` |
| `keywords` | CSV column |
| `app_version` | `legacy` / `v2` / `both` / `unclear` — migration-scoped, see below |
| `surface` | which app the reader opens, from `product_repo_map.package_name` |
| `updated_at` | there is only a `created_at` today |

and makes `url` nullable, since a draft has no URL yet.

### `app_version` is migration scaffolding. `surface` is the durable column.

The enum label is **`v2`**, not `2.0`. Writing `'2.0'` raises `invalid input value for
enum docs_app_version`. Anything that sets this column reads its values from the
migration, not from prose.

`app_version` answers one binary question — does this article describe the original Back
Office or 2.0 — and that question only has a meaningful answer while both exist. It is
there to triage the 38 Back Office / Products articles before 2026-08-17. **Do not
extend it.** Adding a fifth value is the signal that you needed `surface`.

The reason it cannot generalise is the shape of the estate. Oolio is mid-decomposition:
the original POS monorepo (React Native) is being broken into separate React/Remix apps,
capability by capability. Product management already moved out of `pos` into its own app;
`adjustments` and `giftcards` have their own repos; more will follow. Consequences:

- **"Back Office" is not an app.** `product_repo_map` maps ten packages across eight
  repos to the product "Office" — `backoffice-app`, `adjustments-app`, `giftcards/admin`,
  `loyalty-management-app`, `feedback-settings-app`, `orders-management-app`,
  `reservations-management-app`, `tags-backoffice-app`, `tags-merchant-app`, `one`. A
  binary version label cannot say which of the ten a reader should open.
- **The split repeats.** Every capability that leaves the monorepo has its own
  "used to be in POS, now in X" moment. `legacy`/`v2` describes the first one only.
- **A UI uplift is running across all apps**, independently of which app owns what. That
  makes staleness — "verified against what, and when" — the problem that outlives both
  columns. It is not modelled yet, deliberately. Raise it after 2026-08-17.

`surface` is unconstrained text rather than an enum for the same reason: packages land
faster than an enum migration. Validate against `product_repo_map.package_name` at write
time, not in the schema.

### Two known problems with `product_repo_map`

Verified 2026-08-13, both of which affect how agents route from an article to code:

1. **The `products` repo is missing.** `oolio-group/products` is real and active, and it
   is where Back Office 2.0 product management lives — but it has no row. Nothing routes
   an article to it automatically.
2. **The vocabulary does not join to the Tree.** 25 of the 38 rows carry a `product_name`
   that does not exist in `products` — Office, Pay, Insights, Loyalty, Gift Cards,
   Accounts, CDS, Delivery, Feedback, Order Ready Display. Only 13 match. So
   `feature → product → repo` cannot be resolved by join today, and an agent that needs
   the code for a feature has to be told the repo.

Until both are fixed, treat the map as a hint, not a lookup.

## The queries you will actually run

Coverage gap by product:

```sql
select p.name as product,
       count(*) filter (where f.status in ('released','beta','pilot')) as live,
       count(*) filter (where f.status in ('released','beta','pilot')
                          and coalesce(f.link,'') <> '')               as linked
from feature f
left join "featureGroup" g on g.id = f."featureGroupId"
left join products p on p.id = g."productId"
group by p.name order by live desc;
```

Once the join is populated, that second count becomes a join against
`docs_feature_document` where `coverage = 'primary'`, which is the number that actually
means something.

Articles ready to export:

```sql
select slug, title, hubspot_category, hubspot_subcategory, summary, keywords, vault_path
from docs_document
where status = 'approved'
order by hubspot_category, hubspot_subcategory, title;
```

Features with no primary article:

```sql
select p.name, f.name, f.status
from feature f
left join "featureGroup" g on g.id = f."featureGroupId"
left join products p on p.id = g."productId"
left join docs_feature_document d
       on d.feature_id = f.id and d.coverage = 'primary'
left join docs_feature_override o on o.feature_id = f.id
where f.status in ('released','beta','pilot')
  and d.id is null
  and coalesce(o.doc_status,'') <> 'not_required'
order by p.name, f.name;
```

## Rules

- The registry is the truth about *what exists and what state it is in*. The vault is
  the truth about *what the article says*. Never invert that.
- A document with zero `docs_feature_document` rows is valid — hubs, troubleshooting and
  concept pages often map to no single feature. Coverage reporting must not flag these
  as orphans.
- RLS is enabled on every table. Scripts use the service key from `.env`; it is never
  committed.
- The Documentation Knowledge Graph app at `oolio-doc-graph.vercel.app` reads these
  tables. Adding columns is safe; renaming or dropping is not, without checking it first.
