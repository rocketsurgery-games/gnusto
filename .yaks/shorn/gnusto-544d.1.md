---
id: gnusto-544d.1
title: Rename CLAUDE.md -> AGENTS.md; retire .claude/commands/translate-zil.md
type: task
priority: 2
created: '2026-07-11T22:53:35Z'
updated: '2026-07-11T23:01:34Z'
labels:
- tooling
- docs
---

git mv CLAUDE.md AGENTS.md; scan for self-references. Delete the stale .claude/commands/translate-zil.md (superseded by the .agents/skills/translate-zil skill). Add a brief AGENTS.md pointer to the skills and the key gotchas (event-queue contract, 0-falsy).

---
▸ 2026-07-11T23:01:34Z
Done in 2803f4a: git mv CLAUDE.md->AGENTS.md; updated 2 README refs; added Skills pointer + event-queue/0-falsy gotchas; de-referenced retired gnusto-ntr and Claude-Code slash commands. Removed .claude/commands/translate-zil.md.
