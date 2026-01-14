
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

