-- Run once in the Supabase SQL editor.
create table if not exists students (
  id bigint generated always as identity primary key,
  whatsapp_number text not null unique,
  name text
);

create table if not exists food_posts (
  id bigint generated always as identity primary key,
  canteen_number text not null,
  description text not null,
  status text not null default 'open',   -- open | claimed
  claim_deadline text,                   -- "HH:MM"
  claimed_by text,
  created_at timestamptz not null default now()
);
