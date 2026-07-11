---
id: gnusto-544d.4
title: Migrate .claude/skills/tunnel -> .agents/skills (later)
type: task
priority: 3
created: '2026-07-11T22:53:48Z'
updated: '2026-07-11T22:53:48Z'
labels:
- tooling
---

The existing tunnel skill (browser-tunnel test client, TS) still lives under .claude/skills/tunnel with a package-lock and client build. Move it to .agents/skills/tunnel to consolidate on the standard layout. Deferred/риск: verify nothing hard-codes the .claude path and the client build still works after the move; coordinate with any user WIP touching it.
