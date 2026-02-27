---
id: gnusto-9xf.7
title: Implement ritual state machine (professor binds player)
type: task
priority: 2
created: '2026-01-17T14:06:10.384873-05:00'
updated: '2026-02-08T19:07:11.017556Z'
---

Lines 757-762 in walkthrough: Various setup to skip ritual

When player enters alchemy-lab, the professor should:
1. Escort player into lab
2. Bind player in pentagram (tied-up counter)
3. Start ritual that progresses through stages
4. Player must escape before ritual completes

Currently we skip directly to tied-up=3 state.
