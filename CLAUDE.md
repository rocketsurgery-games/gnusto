# Development Philosophy

This is a single-developer research project. There are no other users of this code.
Always prefer hard cutovers to backward-compatible migrations - just change things directly.


# Issue Tracking

This project uses **bd** (beads) for issue tracking.

```bash
bd ready                              # Find available work
bd show <id>                          # View issue details
bd create --title="..." --type=task   # Create new issue
bd update <id> --status=in_progress   # Claim work
bd close <id>                         # Mark complete
bd sync                               # Sync with git remote
```

Do NOT start work on a bead without claiming it.


# Converting ZIL to Grue

When converting ZIL source to Grue, make sure to remove the converted ZIL comments (once fully implemented) as you go.
Make sure to add Grue tests as you go. When discovering bugs in *already converted* code, make their beads P1, so we fix
them before moving on to the rest of the conversion.

# The Grue Language

Remember that we're building a language in the spirit of LISP/Scheme/Clojure, so use those idioms to add language
features that support Interactive Fiction development.

**Standard library:** Add Scheme/Clojure stdlib functions as needed (e.g., `str`, `nth`, `first`, `rest`). Default to
Clojure style, but fall back to Scheme/Racket when Clojure depends on syntax we don't have (like `[vectors]`).
No need to ask permission for obvious stdlib additions.

**Purity:** Keep functions pure. All side-effects must go through the formal effects system (`:effects` in outcomes).
This enables future state-space exploration for winnability analysis.

**LLM interface:** The game will be played via an LLM, so prefer explicit formal action interfaces like
`(do @hacker :ask @master-key)` over fiddly parser-dependent constructs. Don't rely on adjectives or other
parser-level distinctions.

IMPORTANT: As you convert to Grue, always look for opportunities to improve the language design for flexibility and
expressiveness. If you see such an opportunity, or any language construct that isn't generalized, or doesn't behave as
an experienced Scheme/Clojure developer might expect, stop and initiate a discussion with the user.

We're keeping the bead "Language & runtime design tweaks" (frotzlm-ntr) around to capture language changes as we go.
Always track language & runtime improvements & fixes in this epic.


# Session Completion Workflow

When ending a work session, complete ALL steps. Work is NOT complete until `git push` succeeds.

1. **File issues** for remaining work
2. **Run quality gates** if code changed (tests, linters, builds)
3. **Update issue status** - close finished work, update in-progress items
4. **Push to remote** (MANDATORY):
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # Must show "up to date with origin"
   ```
5. **Verify** all changes committed AND pushed
6. **Hand off** - provide context for next session

**Rules:**
- Work is NOT complete until `git push` succeeds
- Never stop before pushing - that leaves work stranded locally
- If push fails, resolve and retry until it succeeds

