# Using Git and GitHub

For a practical first contribution, follow
[Development and release workflow](development_workflow.md). It explains each
step, who performs it, and how to check the result.

## Introduction to Git and GitHub

[Git](https://git-scm.com/) is a distributed version-control system. It records
the history of a project as a sequence of commits, allowing changes to be
reviewed, compared, combined, and recovered. Git works locally and does not
require an internet connection for most operations.

[GitHub](https://github.com/) is an online service that hosts Git repositories
and adds collaboration tools such as pull requests, reviews, issues, releases,
and GitHub Actions. In a research project, Git and GitHub provide:

- A traceable record of changes to code, configuration, and documentation.
- A shared source of truth for collaborators.
- Review and automated testing before changes enter a stable branch.
- A way to associate published results with a precise code version.
- Recovery from accidental changes or lost local files.

GitHub is not a replacement for research-data storage. Do not commit secrets,
credentials, sensitive participant data, generated environments, or large
datasets. This repository uses `.gitignore` to exclude local files and is
intended to use DVC for versioning data and large model artefacts.

Git and GitHub are related but distinct: a *local repository* is the copy and
history on a computer, while a *remote repository* is the copy hosted on
GitHub. Git synchronises them when `fetch`, `pull`, or `push` is run. See
[GitHub's introduction to Git](https://docs.github.com/en/get-started/using-git/about-git)
for more background.

## Basic Git operations

Run Git commands from the repository root unless stated otherwise.

| Command | Purpose |
| --- | --- |
| `git clone <url>` | Download a remote repository and its history for the first time. |
| `git status` | Show the current branch and staged, modified, or untracked files. Run this frequently. |
| `git diff` | Inspect unstaged changes. Use `git diff --staged` to inspect the next commit. |
| `git add <path>` | Stage a specific file or directory for the next commit. |
| `git commit -m "<message>"` | Record the staged changes locally with a concise explanation. |
| `git log --oneline` | Display a compact commit history. |
| `git switch <branch>` | Move to an existing local branch. |
| `git switch -c <branch>` | Create a branch from the current commit and switch to it. |
| `git fetch origin` | Download remote branch information without changing local files. |
| `git pull --ff-only` | Update the current branch only when Git can do so without creating a merge commit. |
| `git push` | Send commits from the current branch to its configured remote branch. |
| `git push -u origin <branch>` | Publish a new branch and remember its upstream branch. |
| `git branch -d <branch>` | Delete a local branch after it has been merged. |

Staging is deliberate: only paths passed to `git add` become part of the next
commit. Always review `git status` and `git diff --staged` before committing.
The official [Git cheat sheet](https://git-scm.com/cheat-sheet.pdf) provides a
compact reference.

## Configuring Git and GitHub

### Install Git and create an account

Install Git using the instructions for the operating system, then confirm it is
available:

```bash
git --version
```

Create a GitHub account, verify its email address, and enable two-factor
authentication. GitHub's [Git setup guide](https://docs.github.com/en/get-started/git-basics/set-up-git)
covers installation and authentication options.

### Set the commit identity

Git stores an author name and email address in every commit. Configure them
globally if the same identity should be used for all repositories:

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

To use a different identity only in the current repository, omit `--global`.
Check the effective values with:

```bash
git config user.name
git config user.email
```

The Git author name does not have to match the GitHub username. Use an email
address associated with the GitHub account, or a GitHub-provided `noreply`
address, if commits should appear on the account without exposing a personal
address. See [setting a Git username](https://docs.github.com/en/get-started/git-basics/setting-your-username-in-git)
for further detail.

### Authenticate with GitHub

GitHub supports HTTPS and SSH remote URLs. A straightforward setup is GitHub
CLI over HTTPS:

```bash
gh auth login
```

Follow the prompts to choose GitHub.com, HTTPS, and browser authentication.
Alternatively, configure an SSH key and use an address such as
`git@github.com:OWNER/REPOSITORY.git`. Account passwords cannot be used for Git
operations over HTTPS; use GitHub CLI, a credential manager, or a personal
access token. The [authentication guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github)
explains the available methods.

Never save access tokens, SSH private keys, passwords, or other credentials in
the repository.

### Check the remote repository

Display the configured remotes:

```bash
git remote -v
```

The conventional name for the primary remote is `origin`. To connect an
existing local repository to a newly created, empty GitHub repository, run one
of the following commands with the correct URL:

```bash
git remote add origin https://github.com/OWNER/REPOSITORY.git
git remote add origin git@github.com:OWNER/REPOSITORY.git
```

Only run one of these commands. A repository created by `git clone` already has
an `origin` remote and does not need another one.

### Repository configuration on GitHub

For a collaborative project, configure the repository on GitHub to:

- Use `main` as the stable default branch.
- Require a pull request before changes can enter `main`.
- Require approval and passing status checks where appropriate.
- Prevent force pushes and deletion of protected branches.
- Enable GitHub Actions needed by the project's workflows.
- Add collaborators or teams with the minimum required access.

These protections are configured under **Settings → Rules → Rulesets**. The
exact controls available can depend on the repository visibility, ownership,
and GitHub plan.

## Pushing to GitHub

Before pushing, inspect and test the local work:

```bash
git status
git diff
uv run pytest
```

Stage only the intended files, review the staged changes, and create a focused
commit:

```bash
git add <path-one> <path-two>
git diff --staged
git commit -m "Describe the change"
```

For the first push of a new branch, set its upstream:

```bash
git push -u origin <branch-name>
```

Later commits on that branch can be sent with:

```bash
git push
```

Pushing publishes commits; it does not merge them into `main`. If Git rejects a
push because the remote branch has moved, fetch the latest state and integrate
it carefully. Do not use `git push --force` on a shared or protected branch.

## Pull request workflow

A [pull request](https://docs.github.com/en/pull-requests/get-started/about-pull-requests)
proposes merging one branch into another. It provides a place to explain the
change, review its diff, discuss it, and run automated checks before merging.

For ordinary changes in this repository, use a short-lived branch based on the
latest `main`. First create a GitHub issue and obtain maintainer approval for
the scope and target semantic version, as described in the
[development and release workflow](development_workflow.md):

```bash
git switch main
git pull --ff-only
git switch -c issue-42/short-description
```

Then follow this workflow:

1. Make one coherent change and add or update its tests and documentation.
2. Review the work with `git status`, `git diff`, and the relevant checks.
3. Stage and commit meaningful groups of changes.
4. Push the branch with `git push -u origin issue-42/short-description` and
   confirm the latest commit passes its GitHub checks.
5. Open a pull request on GitHub with `main` as the base branch.
6. Explain what changed, why it was needed, and how it was tested. Link any
   approved issue and record its target version.
7. Respond to review comments by committing and pushing further changes to the
   same branch; the pull request updates automatically.
8. Merge only after reviews and automated checks pass, then delete the merged
   feature branch.

Release preparation also uses an issue branch from `main` if changes are
needed. Confirm the intended stable version, release notes, tests,
documentation, and reproducible outputs before merging. Tag the reviewed
commit on `main` when ready to publish. The versioning commands are described in
[Semantic versioning with bumpversion](semantic_versioning.md).

When contributing without write access, create a fork, push the branch to that
fork, and open a pull request back to the original repository. GitHub's
[pull request quickstart](https://docs.github.com/en/pull-requests/get-started/pull-request-quickstart)
demonstrates both branch- and fork-based contributions.

## Handling merge conflicts

A conflict occurs when Git cannot automatically combine overlapping changes.
Do not guess at unfamiliar conflicting code. Identify what each side intended,
edit the affected files, run the tests again, and commit the resolution. Ask the
original authors for help when the correct combined behaviour is unclear.

Avoid reducing conflicts by committing generated files unnecessarily. Keep
pull requests focused and update long-running branches regularly.

## Good repository practice

- Commit source code, small configuration files, tests, and documentation.
- Keep commits focused and write messages that explain the change.
- Never commit secrets or sensitive data, even temporarily: Git retains
  history after a file is deleted from the latest revision.
- Review `.gitignore` before adding new tools or generated outputs.
- Use DVC or approved research storage for datasets and large model files.
- Use issues to record planned work, defects, and decisions that need
  discussion.
- Reference a release tag or commit hash when reporting research results.
- Protect `main`; avoid direct commits, forced pushes, and rewritten shared
  history.

## Further reading

- [GitHub: Git basics](https://docs.github.com/en/get-started/git-basics)
- [GitHub: writing code for a project](https://docs.github.com/en/pull-requests/concepts/writing-code-for-a-project)
- [GitHub: about pull requests](https://docs.github.com/en/pull-requests/get-started/about-pull-requests)
- [Pro Git book](https://git-scm.com/book/en/v2)
- [Git command reference](https://git-scm.com/docs)
