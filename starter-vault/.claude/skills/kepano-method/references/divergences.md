# Deliberate divergences from the method

Check here before reporting an audit finding. Everything listed is a decision, not a mistake.
Add to it whenever the vault departs on purpose, with the date and the reason.

- **A folder per kind.** Kepano keeps most notes in two or three folders and lets `categories`
  do the sorting. This vault gives each kind a folder and filters its Base on
  `file.inFolder()`, because a folder is something a script can check: the lint reads the
  kind's template as its schema. Topics still live in `categories`, never in folders.
- **`status` on claim-like kinds** (`draft`, `verified`, `stale`). The method has no such
  field. It exists because a model writes drafts here and a person has to be able to tell
  checked from unchecked.
- **A lint script.** Kepano maintains by hand. This vault checks its own schema because
  sessions write to it, and a session cannot be trusted to remember a style guide.
- **This vault may be one of several.** Rule 1 says one vault. A project vault inside a code
  repo is separate from a personal vault on purpose: different readers, different privacy.
