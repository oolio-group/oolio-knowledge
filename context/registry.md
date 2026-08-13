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
| `app_version` | `legacy` / `v2` / `both` / `unclear` — the distinction that makes the Products triage possible |
| `updated_at` | there is only a `created_at` today |

and makes `url` nullable, since a draft has no URL yet.

### `app_version` is provisional — do not build on it yet

The enum label is **`v2`**, not `2.0`. Writing `'2.0'` raises `invalid input value for
enum docs_app_version`. Anything that sets this column reads its values from the
migration, not from prose.

The four values are enough to triage the 38 Back Office / Products articles, which is
the job they were added for, and they are **not** settled as a general versioning model.
Two known weaknesses:

- `both` and `unclear` are doing different jobs — "accurate for either app" versus "we
  have not looked yet" — and only one of those is a finished state. A triage pass that
  leaves rows at `unclear` has not finished.
- A per-document enum cannot express an article that is *mostly* right for 2.0 with two
  wrong steps. Today that is `update` in the reconciler's verdict and `both` here, which
  loses the distinction between "covers both apps deliberately" and "needs small
  corrections".

If versioning turns out to need more than a per-article label, this column is the wrong
shape and should be replaced rather than extended. Flag it before adding a fifth value.

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
