---
name: review-pr
description: Review an ADK pull request or local branch against the repo's review checklist (REVIEW.md) and report blocking issues and nits. Use when asked to review a PR in the polyai-adk repo, or to self-review a branch before opening one.
metadata:
  internal: true
---

# Review an ADK change

1. Get the change.
   - A PR: `gh pr view <number>` for the title and description, and `gh pr diff <number>`.
   - A local branch: `git log --oneline main..HEAD` and `git diff main...HEAD`.
2. Read `REVIEW.md` at the repo root and apply every item to the diff, the PR title and the
   description. For anything that touches resources or commands, also read
   `src/poly/resources/AGENTS.md` or `src/poly/cli_commands/AGENTS.md`.
3. Check the claims against the code. Open the files around each change before flagging it, and
   drop anything you can't point to a line for.
4. Skip everything on REVIEW.md's ignore list.

## Report

1. **Summary:** what the change does, in one or two sentences.
2. **Blocking:** each issue with `file:line`, what's wrong and the fix.
3. **Worth raising** and **nits**, in the same format and kept short.
4. **Verdict:** approve, request changes or comment.

If you're asked to post the review, use `gh pr review <number>` with the report as the body, and
only after the user confirms.
