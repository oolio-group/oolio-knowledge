# The publishing contract — CSV and HTML

HubSpot's knowledge base has **no API**. Everything published goes through a CSV import.
That constrains how articles are drafted, so read this before writing, not after.

## The eight columns

```
URL, TITLE, CATEGORY, SUBCATEGORY, ARTICLE_BODY, KEYWORDS, META_DESCRIPTION, SUBTITLE
```

| Column | Maps to | Notes |
|---|---|---|
| `URL` | `docs_document.url` | See the unresolved question below |
| `TITLE` | `docs_document.title` | Sentence case, verb-led for tasks |
| `CATEGORY` | `docs_document.hubspot_category` | Tier 1 — one of only two available |
| `SUBCATEGORY` | `docs_document.hubspot_subcategory` | Tier 2 — the last one available |
| `ARTICLE_BODY` | the draft, converted | HTML, see below |
| `KEYWORDS` | `docs_document.keywords` | Comma-separated, lowercase |
| `META_DESCRIPTION` | `docs_document.summary` | One sentence, what the reader will learn |
| `SUBTITLE` | first line of the body, or blank | Optional in the sample |

## Constraint 1 — only two levels of hierarchy

`CATEGORY` and `SUBCATEGORY` is the whole taxonomy.

The IA in the HubSpot Wiki Proposal §8 has **three** tiers: the top-level groups
(Get started / Run your venue / Keep it running), then sixteen categories, then
subcategories. One tier cannot be expressed in the CSV.

**This must be resolved before drafting**, because it determines the `CATEGORY` value of
every article. Two options:

- the three top groups become presentational only, living in the help centre's
  navigation rather than in article metadata; the sixteen become `CATEGORY`
- or the three become `CATEGORY` and the sixteen collapse into `SUBCATEGORY`, losing the
  subcategory level entirely

The first preserves more structure. Neither is free.

## Constraint 2 — the body is HTML, and a narrow subset

Observed in HubSpot's own sample export:

```html
<div id="post-body">
  <p>Plain paragraph.</p>
  <p><a href="https://…">A link</a></p>
  <p class="alert"><strong>Please note:</strong> a callout is a CSS class on a
     paragraph, not a component.</p>
  <span class="tag-name">Design Manager</span>
</div>
```

Write to this ceiling:

**Safe** — `<p>`, `<a href>`, `<strong>`, `<em>`, `<ul>`/`<ol>`/`<li>`, `<h2>`/`<h3>`,
`<p class="alert">` for callouts.

**Verify before relying on** — `<table>`, nested lists, `<img>`, `<code>`/`<pre>`,
anchors within a page.

**Avoid** — anything requiring CSS or JS you do not control, custom classes beyond
`alert` and `tag-name`, iframes, embedded video, accordions, tabs.

Practical consequence: **do not draft comparison tables or deeply nested procedures**
until table support is confirmed. Restructure as sequential headed sections instead.

## Constraint 3 — the unresolved question

`URL` is a column, which tells you this format was designed for *migrating existing
pages from another CMS*, not for authoring new ones. Two things follow, and neither is
confirmed:

1. **Can `URL` be blank for a net-new article**, or does HubSpot require it?
2. **Does re-importing the same `URL` update the existing article, or create a
   duplicate?**

If it duplicates, every correction after publication has to be typed by hand into
HubSpot, and the drafting pipeline is one-way. That would change the economics of this
entire project.

**Verify this before the first real import.** Test with two articles in a sandbox:
import, edit, re-import, and see what you get.

## Constraint 4 — cross-links and the slug

Articles cannot link to each other until their URLs exist, and their URLs do not exist
until they are imported.

Solution: **assign the slug up front**, in the draft frontmatter, and write internal
links as `[[slug:create-a-menu]]`. `build_csv.py` resolves those to
`https://help.oolio.com/<slug>` at build time. The slug never changes once assigned —
changing it breaks every link pointing at it, and breaks the registry join.

If HubSpot rejects a chosen slug at import, fix it in the registry and rebuild the CSV.
Never fix it by hand in HubSpot, or the registry stops being the truth.

## Constraint 5 — no status column

There is no way to import an article as a draft. Everything in the CSV is publishable
content. Draft state lives in the registry (`docs_document.status`), and only rows at
`status = 'approved'` are ever exported.
