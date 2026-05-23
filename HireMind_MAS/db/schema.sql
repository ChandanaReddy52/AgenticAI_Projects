-- ================================================================
-- HireMind Supabase Schema
-- Run in Supabase SQL Editor to initialise the database.
-- ================================================================

-- pgvector: required for embedding storage and similarity search
create extension if not exists vector;

-- ── Candidates ───────────────────────────────────────────────
-- Populated exclusively by an external ingestion script.
-- The embedding column is set by that script using
-- text-embedding-3-small (1536 dims) on the resume field.
create table if not exists candidates (
    id         uuid        primary key default gen_random_uuid(),
    name       text        not null,
    email      text        not null unique,
    resume     text        not null,
    embedding  vector(1536),
    created_at timestamptz not null default now()
);

-- ── match_candidates RPC function ────────────────────────────
-- Returns the top 5 candidates most semantically similar to the
-- provided job-description embedding.
-- Called by vector_store.search_candidates().
create or replace function match_candidates(query_embedding vector(1536))
returns table (
    id         uuid,
    name       text,
    email      text,
    resume     text,
    similarity float
)
language sql stable as $$
    select
        id,
        name,
        email,
        resume,
        1 - (embedding <=> query_embedding) as similarity
    from candidates
    where embedding is not null
    order by embedding <=> query_embedding
    limit 5;
$$;

-- ── Jobs ─────────────────────────────────────────────────────
create table if not exists jobs (
    id                   uuid        primary key default gen_random_uuid(),
    title                text        not null,
    description          text        not null,
    required_skills      text[]      not null default '{}',
    nice_to_have_skills  text[]      not null default '{}',
    experience_years_min int         not null default 0,
    location             text,
    remote_ok            boolean     not null default false,
    status               text        not null default 'OPEN'
                           check (status in ('OPEN', 'CLOSED', 'PAUSED')),
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

-- ── Applications ──────────────────────────────────────────────
create table if not exists applications (
    id                        uuid        primary key default gen_random_uuid(),
    job_id                    uuid        not null references jobs(id) on delete cascade,
    candidate_id              uuid        not null references candidates(id) on delete cascade,
    status                    text        not null default 'APPLIED'
                                check (status in (
                                    'APPLIED', 'SCREENING', 'SHORTLISTED',
                                    'INTERVIEW_SCHEDULED', 'EVALUATION',
                                    'HIRED', 'REJECTED', 'ON_HOLD'
                                )),
    -- Set by Screening Agent
    screening_score           numeric(5,2),   -- 0–100
    screening_decision        text check (screening_decision in ('SHORTLIST', 'REJECT')),
    screening_reasoning       text,
    -- Set by Evaluation Agent
    technical_score           numeric(4,1),   -- 0–10
    culture_fit_score         numeric(4,1),
    overall_score             numeric(4,1),
    recommendation            text check (recommendation in ('HIRE', 'NO_HIRE', 'HOLD')),
    evaluation_rationale      text,
    created_at                timestamptz not null default now(),
    updated_at                timestamptz not null default now(),
    unique (job_id, candidate_id)
);

-- ── Interviews ────────────────────────────────────────────────
create table if not exists interviews (
    id             uuid        primary key default gen_random_uuid(),
    application_id uuid        not null references applications(id) on delete cascade,
    scheduled_at   timestamptz not null,
    meeting_link   text,
    notes          text,
    completed      boolean     not null default false,
    created_at     timestamptz not null default now()
);

-- ── Agent audit log ───────────────────────────────────────────
create table if not exists agent_logs (
    id           uuid        primary key default gen_random_uuid(),
    agent        text        not null,
    action       text        not null,
    job_id       uuid        references jobs(id),
    candidate_id uuid        references candidates(id),
    meta         jsonb       not null default '{}',
    created_at   timestamptz not null default now()
);

-- ── Auto-update updated_at ────────────────────────────────────
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger trg_jobs_updated_at
    before update on jobs
    for each row execute function set_updated_at();

create trigger trg_applications_updated_at
    before update on applications
    for each row execute function set_updated_at();

-- ── Row-Level Security ────────────────────────────────────────
alter table candidates   enable row level security;
alter table jobs         enable row level security;
alter table applications enable row level security;
alter table interviews   enable row level security;
alter table agent_logs   enable row level security;

-- The service role key (used by backend agents) bypasses RLS.
create policy "service role bypass" on candidates   for all using (true) with check (true);
create policy "service role bypass" on jobs         for all using (true) with check (true);
create policy "service role bypass" on applications for all using (true) with check (true);
create policy "service role bypass" on interviews   for all using (true) with check (true);
create policy "service role bypass" on agent_logs   for all using (true) with check (true);
