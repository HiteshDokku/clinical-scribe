# ADR-0002: Three-tier data retention

**Status:** accepted
**Date:** 2026-09-20
**Owner:** Hitesh Dokku

## Context

The synopsis's "ephemeral data processing" claim (audio and transcripts
purged immediately) is a clean privacy story but a poor medico-legal
records story: if a note is later disputed, the hospital has no way to
show provenance.

## Decision

Three explicit retention tiers, each with a different mechanism:

1. **Audio** — never written to disk under any configuration. Held in a
   bounded RAM ring buffer (`ASR_MAX_BUFFER_SECONDS`), zeroed at session
   end. `AUDIO_RETENTION=never` is not a configurable option in
   `docker-compose.prod.yml`.
2. **Transcript** — retained only if the clinician opts in per encounter
   (`TRANSCRIPT_RETENTION_DEFAULT=off`). Held in Redis with a TTL
   (`TRANSCRIPT_TTL_SECONDS`) by default; deleted on sign-off unless opted
   in, in which case it moves to a `note_versions`-adjacent table.
3. **Note versions + audit log** — retained permanently. Every AI-drafted
   version and every clinician edit is stored as a diff in the append-only
   `audit_log` table (see ADR-0003 in the architecture doc's audit
   section), along with model name, model hash, and prompt version. The
   audit log stores diffs of clinical *text*, never raw audio.

## Consequences

- The system can answer "who wrote this line, and what did the AI
  originally draft" indefinitely, which a fully ephemeral design cannot.
- Storage of transcripts becomes a deliberate, logged clinician action
  rather than a silent default — this is also a stronger consent story.
- `audio` remaining un-retainable in all configurations is the property
  that keeps the "device compromise cannot expose a backlog of
  recordings" safety claim true.

## Alternatives considered

- **Fully ephemeral (as originally specified):** rejected — undermines
  auditability and dispute resolution.
- **Retain everything, always:** rejected — defeats the privacy-hardened
  premise of the entire project and multiplies breach impact.
