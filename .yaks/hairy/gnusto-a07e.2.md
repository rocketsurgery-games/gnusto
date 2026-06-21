---
id: gnusto-a07e.2
title: 'filfre: dependency-ordered generation with edit + ref modes'
type: feature
priority: 2
created: '2026-06-21T20:29:49Z'
updated: '2026-06-21T20:29:49Z'
depends_on:
- gnusto-a07e.1
labels:
- render
- image
---

Make filfre fill generate in dependency order, threading prior outputs as inputs. Prototype is experiments/consistency/probe.py (toposort runner + gen(refs=...)).

- Topo-sort the manifest dep graph; generate roots first, then dependents.
- M2 ref mode: pass the referenced key's image(s) as reference (generate_image_nanobanana already accepts reference_images).
- M3 edit mode: pass the base image + an 'keep everything, change only X' instruction (the delta).
- Resume-from-disk (skip keys already present; --force to regenerate) so a bad root can be re-rolled without redoing the subtree.
- SDK gotcha proven in the probe: cache ONE google-genai Client() (a fresh per-call client throws 'client has been closed'); port this fix to filfre + experiments/style-rough.

Caveat to handle: chained edits accumulate finish/detail and drift off the rough style -> add a style-reassertion clause and/or cap chain length.
