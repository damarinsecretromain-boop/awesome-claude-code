-- Schéma du clone TrendStory (usage interne).
-- Postgres sur Supabase. Accès : row level security, chaque table porte user_id
-- (dénormalisé sur les tables enfants pour garder des règles simples).
-- Le worker (Trigger.dev) écrit avec la clé service_role, qui contourne la RLS.
-- Les coûts sont en micro-dollars (bigint) : une image coûte une fraction de cent.

create extension if not exists pgcrypto;

-- Mise à jour automatique de updated_at
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- ---------------------------------------------------------------- profils
-- Une ligne par utilisateur de auth.users (créée au premier login).
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  locale text not null default 'fr',
  monthly_budget_microusd bigint check (monthly_budget_microusd >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- univers
-- Les « thèmes » : réglages visuels réutilisables (style, éclairage, prompts
-- de base). Les tiens, pas ceux de TrendStory.
create table universes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  name text not null,
  style_prompt text not null,
  negative_prompt text,
  default_image_model text,
  default_video_model text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, name)
);
create index on universes (user_id);

-- ---------------------------------------------------------------- personnages
create table characters (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  universe_id uuid references universes(id) on delete set null,
  name text not null,
  description text not null,          -- apparence, réinjectée dans chaque prompt
  personality text,
  voice_id text,                      -- voix TTS attribuée
  source text not null check (source in ('prompt','photo','preset')),
  photo_consent boolean not null default false,
  -- clés de stockage (R2) des images de référence ; la première sert de fiche
  reference_keys text[] not null default '{}',
  status text not null default 'draft' check (status in ('draft','generating','ready','failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint photo_needs_consent check (source <> 'photo' or photo_consent)
);
create index on characters (user_id, created_at desc);
create index on characters (universe_id);

-- ---------------------------------------------------------------- séries
create table series (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  universe_id uuid not null references universes(id) on delete restrict, -- fixé à la création
  title text not null,
  aspect_ratio text not null default '9:16' check (aspect_ratio in ('9:16','16:9')),
  language text not null default 'fr',
  story_so_far text not null default '',  -- résumé tenu à jour après chaque épisode
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index on series (user_id, updated_at desc);
create index on series (universe_id);

create table series_characters (
  series_id uuid not null references series(id) on delete cascade,
  character_id uuid not null references characters(id) on delete restrict, -- pas de perso supprimé sous une série
  user_id uuid not null references profiles(id) on delete cascade,
  primary key (series_id, character_id)
);
create index on series_characters (character_id);
create index on series_characters (user_id);

-- ---------------------------------------------------------------- projets (= une vidéo)
create table projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  mode text not null check (mode in ('agent','express','series','studio')),
  series_id uuid references series(id) on delete cascade,
  episode_number int check (episode_number > 0),
  universe_id uuid references universes(id) on delete set null,
  title text,
  idea text not null default '',
  aspect_ratio text not null default '9:16' check (aspect_ratio in ('9:16','16:9')),
  language text not null default 'fr',
  max_duration_s int not null default 60 check (max_duration_s between 5 and 180),
  status text not null default 'draft'
    check (status in ('draft','scripting','generating','assembling','ready','failed')),
  script jsonb,                       -- sortie structurée du LLM (scènes, dialogues)
  music_key text,
  subtitles_key text,
  final_video_key text,
  duration_s numeric(6,2),
  estimated_cost_microusd bigint,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint episode_needs_series check ((series_id is null) = (episode_number is null))
);
create index on projects (user_id, created_at desc);
create index on projects (user_id, status);
create index on projects (universe_id);
create unique index projects_one_episode_number on projects (series_id, episode_number)
  where series_id is not null;

-- ---------------------------------------------------------------- scènes
create table scenes (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  user_id uuid not null references profiles(id) on delete cascade,
  position int not null check (position >= 0),
  narration text,
  dialogue jsonb not null default '[]',   -- [{character_id, line}]
  image_prompt text not null,
  motion_prompt text,
  image_model text not null,
  video_model text not null,
  duration_s numeric(4,1) not null check (duration_s > 0 and duration_s <= 15),
  image_key text,
  clip_key text,
  voice_key text,
  voice_timestamps jsonb,                 -- alignement mot à mot pour les sous-titres
  status text not null default 'pending'
    check (status in ('pending','image','video','voice','ready','failed')),
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint scene_position_unique unique (project_id, position) deferrable initially deferred
);
create index on scenes (user_id);

create table scene_characters (
  scene_id uuid not null references scenes(id) on delete cascade,
  character_id uuid not null references characters(id) on delete restrict,
  user_id uuid not null references profiles(id) on delete cascade,
  primary key (scene_id, character_id)
);
create index on scene_characters (character_id);
create index on scene_characters (user_id);

-- ---------------------------------------------------------------- jobs de génération
-- Un appel à un fournisseur (LLM, image, vidéo, voix, musique, montage).
-- Sert aussi de journal des coûts.
create table generation_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  project_id uuid references projects(id) on delete cascade,
  scene_id uuid references scenes(id) on delete cascade,
  character_id uuid references characters(id) on delete cascade,
  step text not null
    check (step in ('script','character','image','video','voice','music','subtitles','assemble','summary','agent')),
  provider text not null,              -- anthropic, google, fal, elevenlabs, local
  model text not null,
  idempotency_key text not null unique,  -- ex. scene_id:video:attempt
  provider_request_id text,
  status text not null default 'queued'
    check (status in ('queued','running','succeeded','failed','cancelled')),
  attempt int not null default 1 check (attempt >= 1),
  input jsonb not null default '{}',
  output jsonb,
  cost_microusd bigint not null default 0 check (cost_microusd >= 0),
  error text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint job_has_target check (num_nonnulls(project_id, scene_id, character_id) >= 1)
);
create index on generation_jobs (user_id, created_at desc);
create index on generation_jobs (project_id);
create index on generation_jobs (scene_id);
create index on generation_jobs (character_id);
create index on generation_jobs (status) where status in ('queued','running');
-- un seul montage en cours par projet
create unique index one_active_assemble on generation_jobs (project_id)
  where step = 'assemble' and status in ('queued','running');

-- ---------------------------------------------------------------- messages de l'agent
create table agent_messages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  user_id uuid not null references profiles(id) on delete cascade,
  seq int not null,
  role text not null check (role in ('user','assistant')),
  content jsonb not null,             -- blocs bruts de l'API, renvoyés tels quels
  created_at timestamptz not null default now(),
  unique (project_id, seq)
);
create index on agent_messages (user_id);

-- ---------------------------------------------------------------- triggers updated_at
do $$
declare t text;
begin
  foreach t in array array['profiles','universes','characters','series','projects','scenes','generation_jobs']
  loop
    execute format('create trigger %I_updated_at before update on %I
                    for each row execute function set_updated_at()', t, t);
  end loop;
end $$;

-- ---------------------------------------------------------------- RLS
do $$
declare t text;
begin
  foreach t in array array['universes','characters','series','series_characters','projects',
                           'scenes','scene_characters','generation_jobs','agent_messages']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('create policy %I_owner on %I for all
                    using (user_id = auth.uid()) with check (user_id = auth.uid())', t, t);
  end loop;
end $$;

alter table profiles enable row level security;
create policy profiles_owner on profiles for all
  using (id = auth.uid()) with check (id = auth.uid());

-- Les jobs et leurs coûts ne sont écrits que par le worker : lecture seule côté client.
drop policy generation_jobs_owner on generation_jobs;
create policy generation_jobs_read on generation_jobs for select using (user_id = auth.uid());
