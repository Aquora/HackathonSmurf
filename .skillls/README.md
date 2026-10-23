# Project-local skill copies

All 13 entries in [the team catalog](../docs/skills.md) are stored here using the
owner-requested `.skillls/` spelling. Eight are copies of locally available skills;
five were downloaded from the official openai/skills curated repository.

Read `<skill-name>/SKILL.md` explicitly when using a relevant skill. Do not load all
skills for every task. This custom directory is a shared library, not automatic
registration in every teammate's chatbot. Copies are available to read immediately,
including on the next turn; native discovery depends on that chatbot's configuration.
No global installation or chatbot settings were changed.

Supporting scripts, references, assets, and included license files were preserved.
[manifest.json](manifest.json) records origins and per-file SHA-256 checksums. Remote
copies were fetched from main, not a recorded commit; local upstream revisions are
unknown. Downloaded/copied does not mean mandatory, tested, or configured.

## Compatibility notes

- Some scripts assume a global skills directory. Resolve them relative to the
  local skill folder when invoking them explicitly; do not change system/home
  variables or assume global installation. Upstream content is preserved unchanged.
- Review skills need their named specialized subagents. Copying instructions does
  not create those agents. Deployment skills need their provider tools/accounts;
  the Vercel skill includes an origin-specific workflow that may not fit GitHub.
- Playwright needs Node/npx and its browser tooling; gh-fix-ci needs authenticated
  GitHub CLI; Sentry needs its CLI and authorized account context. Security guidance
  covers the languages/frameworks documented by that skill.
- Downloading these skills does not execute their scripts, install dependencies,
  authorize service actions, or select deployment providers. Read their requirements
  and apply the current task authorization and root project instructions.
