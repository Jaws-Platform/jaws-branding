# Contributing

`jaws-branding` holds the Jaws brand: the logo, the avatars, the README
banner, and the standard every Jaws repository's README header follows.
Other repositories link to its files on `main`, so it has no build step and
deploys nothing. Coding agents should read [AGENTS.md](AGENTS.md).

## Local development setup

Requirements: Node.js 24, [uv](https://docs.astral.sh/uv/),
[pre-commit](https://pre-commit.com) and the GitHub CLI (`gh`).

```sh
git clone https://github.com/Jaws-Platform/jaws-branding.git
cd jaws-branding
npm ci                                         # commitlint
pre-commit install --hook-type commit-msg      # local commit-msg hook
```

The `commit-msg` hook runs commitlint locally. It is a convenience only;
**CI is the authoritative check**.

## Commits

Each commit message is a **single-line** Conventional Commit:

```
type(scope)?: subject
```

- At most 100 characters.
- Allowed types: `feat`, `fix`, `docs`, `chore`, `refactor`, `ci`, `build`,
  `perf`, `style`, `test`, `revert`.
- Breaking changes are marked with `!`, for example `feat!: drop the old banner`.
- The **only** content allowed after the header is a blank line followed by
  `Co-authored-by: Name <email>` trailers. No body text. Details belong in the
  pull request description.

commitlint enforces this (`@commitlint/config-conventional` plus the local
`only-coauthor-trailers` rule in `tools/commitlint/`). The fixtures in
`tests/commitlint/` show accepted and rejected messages; CI checks them.

## Pull requests

- After the initial scaffold commit, **every change reaches `main` through a
  pull request**. Direct pushes are blocked.
- Merges are **squash or rebase only**. No merge commits; history is linear.
- The **title must be a valid Conventional Commit**, because a squash merge
  uses it as the commit message.
- Use the typed template for your change and fill in every section:

  ```sh
  gh pr create --template feat.md      # or fix.md, docs.md, chore.md, refactor.md, ci.md
  ```

  In the browser, append `?template=<type>.md` to the compare URL. `fix.md`
  also asks for Bug, Root cause and Reproduction.

CI runs these jobs on every pull request, and all of them are required on
`main`:

| Job | Checks |
|---|---|
| `commitlint` | Every commit in the range `base..head`, so rebase-merged commits are all checked |
| `pr-title` | The title is a Conventional Commit and passes the commit header rules |
| `commitlint-rules` | Unit tests for the local rule, and the fixture messages |

## Repository settings

`scripts/apply-repo-settings.sh` applies the settings through the GitHub API:

- Squash and rebase merges only; squash commits use the pull request title and
  a blank body. Head branches are deleted after merge.
- A ruleset on `main` requires a pull request, squash or rebase merges, every
  CI job as a status check and linear history, and blocks force pushes and
  deletion, with no bypass actors.
