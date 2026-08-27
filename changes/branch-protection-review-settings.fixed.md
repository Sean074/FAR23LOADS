- **The branch-protection guard reaches the review settings, and three promises
  `main` never kept are corrected (CR-D-4's class, tier S, 2026-08-26).** The
  guard added with #46 tracked `required_pull_request`, which is true the moment
  GitHub carries *any* review block for the branch — so `DEVELOPMENT_PROCESS.md`
  §2 could promise "one approving review from someone other than the author",
  "review from Code Owners required" and "stale approvals dismissed on push"
  against a block that required none of the three, and no hop-1 assertion could
  see it. The snapshot now tracks `required_approving_review_count`,
  `required_code_owner_reviews`, `dismiss_stale_reviews` and
  `required_conversation_resolution`, and the first `--check` run against live
  `main` found exactly that drift: all three off, conversation resolution the
  only one live.
- **The prose is corrected, not the branch — the settings split by profile.**
  The three review requirements are the multi-dev profile's target and are off
  under §0's solo profile deliberately: GitHub does not let an author approve
  their own pull request, and `.github/CODEOWNERS` names one person on every
  line, so either setting would block **every** merge — the milestone PR
  included — until a second collaborator exists. Turning them on joins restoring
  squash-merge in the switch-over list. §2 now states both profiles, as it
  already did for the merge method, and
  `test_the_process_docs_agree_with_the_live_review_settings` holds the prose to
  whichever way the settings are set, in both directions: the "OFF under §0"
  bullet is required while they are off and must go when they come on.
