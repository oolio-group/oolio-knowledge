-- 001_docs_document_lifecycle.sql
--
-- Lets docs_document represent an article that is not published yet.
--
-- Today url is NOT NULL and unique and there is no status, so a draft living in the
-- my_brain vault cannot be represented at all. This adds the lifecycle, the stable
-- slug, the vault pointer and the HubSpot CSV fields.
--
-- Additive only. The Documentation Knowledge Graph app (oolio-doc-graph.vercel.app)
-- reads these tables, so nothing is renamed or dropped.
--
-- Review before running. Run in the Supabase SQL editor or via apply_migration.

begin;

-- ---------------------------------------------------------------- lifecycle

do $$ begin
  create type docs_status as enum (
    'planned',     -- identified as needed, nothing written
    'drafting',    -- being written in the vault
    'in_review',   -- with a human or the accuracy-reviewer
    'approved',    -- passed review, eligible for CSV export
    'published',   -- live in HubSpot, url populated
    'retired'      -- withdrawn; row kept for history
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type docs_page_type as enum (
    'task',        -- the how-to
    'hub',
    'track',
    'reference',
    'fix',         -- the troubleshooting guide
    'concept',
    'release',
    'known_issue'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type docs_app_version as enum ('legacy', 'v2', 'both', 'unclear');
exception when duplicate_object then null; end $$;

-- ---------------------------------------------------------------- columns

alter table public.docs_document
  add column if not exists status               docs_status      not null default 'published',
  add column if not exists slug                 text,
  add column if not exists vault_path           text,
  add column if not exists page_type            docs_page_type,
  add column if not exists hubspot_category     text,
  add column if not exists hubspot_subcategory  text,
  add column if not exists keywords             text,
  add column if not exists app_version          docs_app_version not null default 'unclear',
  add column if not exists body_html            text,
  add column if not exists updated_at           timestamptz      not null default now();

comment on column public.docs_document.status is
  'Lifecycle. Only approved rows are exported to the HubSpot CSV.';
comment on column public.docs_document.slug is
  'Stable identity, assigned before publication. Resolves [[slug:...]] cross-links. Never change once set.';
comment on column public.docs_document.vault_path is
  'Path to the draft body in the my_brain vault, relative to vault root.';
comment on column public.docs_document.app_version is
  'Which application this article describes. legacy = original Back Office, v2 = Back Office 2.0.';
comment on column public.docs_document.body_html is
  'Cache of the live page body, populated when triaging. Not the source of truth for drafts.';
comment on column public.docs_document.hubspot_category is
  'CSV CATEGORY. Separate from the legacy section/category columns, which describe the current live IA.';

-- existing 161 rows are live articles
update public.docs_document
   set status = 'published'
 where status is null;

-- ---------------------------------------------------------------- url nullable

-- A draft has no URL until it is imported.
alter table public.docs_document
  alter column url drop not null;

-- ---------------------------------------------------------------- constraints

-- Slug unique where present.
create unique index if not exists docs_document_slug_key
  on public.docs_document (slug)
  where slug is not null;

-- A published article must have somewhere to point.
alter table public.docs_document
  drop constraint if exists docs_document_published_needs_url;
alter table public.docs_document
  add constraint docs_document_published_needs_url
  check (status <> 'published' or url is not null);

-- An approved article must have everything the CSV needs.
alter table public.docs_document
  drop constraint if exists docs_document_approved_needs_csv_fields;
alter table public.docs_document
  add constraint docs_document_approved_needs_csv_fields
  check (
    status not in ('approved', 'published')
    or (slug is not null
        and hubspot_category is not null
        and hubspot_subcategory is not null
        and coalesce(summary, '') <> '')
  );

-- ---------------------------------------------------------------- updated_at

create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists docs_document_touch on public.docs_document;
create trigger docs_document_touch
  before update on public.docs_document
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------- helper view

create or replace view public.docs_coverage as
select p.name                                            as product,
       g.name                                            as feature_group,
       f.id                                              as feature_id,
       f.name                                            as feature,
       f.status                                          as feature_status,
       o.doc_status                                      as override_status,
       count(d.id) filter (where d.coverage = 'primary')    as primary_docs,
       count(d.id) filter (where d.coverage = 'supporting') as supporting_docs,
       count(d.id) filter (where d.coverage = 'stale')      as stale_docs
  from public.feature f
  left join public."featureGroup" g on g.id = f."featureGroupId"
  left join public.products p       on p.id = g."productId"
  left join public.docs_feature_document d on d.feature_id = f.id
  left join public.docs_feature_override  o on o.feature_id = f.id
 group by p.name, g.name, f.id, f.name, f.status, o.doc_status;

comment on view public.docs_coverage is
  'Per-feature documentation coverage. A feature with override_status = not_required is
   deliberately undocumented and should be excluded from gap metrics.';

commit;

-- ------------------------------------------------------------------------------
-- Not done here, deliberately:
--
-- Migrating feature.link into docs_feature_document. That is a data migration with
-- judgement in it (which coverage level does each existing link represent?) and it
-- should run as a reviewed script, not silently inside a schema change. 128 features
-- carry a link today.
-- ------------------------------------------------------------------------------
