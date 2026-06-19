---
id: gnusto-ntr.22
title: 'Keyword vs string semantics: stop conflating :keyword with same-named string'
type: bug
priority: 2
created: '2026-06-19T22:09:29Z'
updated: '2026-06-19T22:28:16Z'
labels:
- lang
- render
---

In a Lisp-family language a keyword :open and the string "open" are DISTINCT values that are not equal. Our runtime mostly honors this (the evaluator self-evaluates keywords as Keyword objects, and (= :open "open") is correctly false) — but the *static lowering* layer conflates them, which is a footgun and the blocker for the :render/:rdesc cleanup.

Concretely:
- parse_properties lowers keyword map KEYS to bare strings: :rdesc (:open "...") -> {"open": ...}. So a variant declared as keyword :open is stored as the string "open".
- sexpr_to_value lowers keyword VALUES to ":open" (WITH the colon) — inconsistent with the key path (no colon). Same source keyword, two different lowerings.
- The :render selector must RETURN a string ("open"); resolve_asset_key does str(result), so returning the natural keyword :open yields ":open" -> key "microwave-:open" (broken). So the variant token is authored as a keyword in :rdesc but a string in :render, and only works because of the lossy key-lowering.

Net: the same concept (a variant tag) is two lexical classes, matched only via lossy/asymmetric keyword->string lowering.

Goal: treat keywords as first-class, self-denoting, interned-by-name values distinct from strings throughout, including the static lowering used by properties / :rdesc / context. Pick one consistent representation so keyword keys and values round-trip without colon-stripping inconsistencies, and so (= :open "open") stays false everywhere (parser, static maps, runtime).

This is a prerequisite for the :render/:rdesc + event-beat cleanup (keyword = variant tag, string = verbatim alias). Do this first, then migrate existing game code (the two (fn) selectors returning "open"/"closed"/"running", and any :rdesc maps) to the accurate form.
