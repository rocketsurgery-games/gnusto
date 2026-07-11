---
id: gnusto-544d
title: Migrate agent config to AGENTS.md + .agents/skills
type: task
priority: 2
created: '2026-07-11T22:52:58Z'
updated: '2026-07-11T23:17:33Z'
labels:
- tooling
- docs
---

We no longer use Claude Code. Move to the standard agent layout: AGENTS.md for project instructions (was CLAUDE.md) and project-local skills under .agents/skills/<name>/SKILL.md (name+description frontmatter). Current state: root CLAUDE.md; stale .claude/commands/translate-zil.md (obsolete syntax + says 'do not copy text', which contradicts the engine-authoritative decision in gnusto-7256); a .claude/skills/tunnel/ skill with a TS client. Rewrite translation guidance and add a testing skill covering the patterns we keep re-deriving.

---
▸ 2026-07-11T23:17:33Z
Done (commit 2803f4a). CLAUDE.md->AGENTS.md + skills pointer/gotchas; new translate-zil and grue-testing skills; stale .claude command removed. .4 (tunnel migration) slaughtered -- user tossed the tunnel skill instead. All children resolved.
