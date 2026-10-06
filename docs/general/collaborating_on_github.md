# From an issue to a pull request

Use this walkthrough to make a change to a shared project and have someone
review it. The sequence is: **describe the work in an issue → create a branch →
make and check changes → open a pull request → review and merge**.

The example is a small documentation improvement: clarify the installation
instructions in `README.md`. It works the same way for code changes. Replace
issue number `42`, branch name `issue-42/installation-docs`, and example file
paths with your own. Only run the commands appropriate to your current step.

## Who does what?

| Person | Responsibility |
| --- | --- |
| Contributor | Creates the issue, makes the change on a branch, checks it and opens a pull request. |
| Reviewer | Reads the proposed changes, checks the evidence and requests corrections or approves. |
| Maintainer | Agrees the scope, identifies required checks and merges approved changes. |
| Admin | Grants access and configures repository rules when needed. |

One person may hold several roles. GitHub permissions determine which actions
they can perform; the team agrees who is responsible for each action.

## Words you will see

**Git** records changes on your computer; **GitHub** holds the shared copy online.

| Word | Meaning |
| --- | --- |
| Issue | A numbered discussion of a problem or proposed improvement. |
| Repository | The project files and their recorded history. Often shortened to “repo”. |
| Branch | A named line of work where you prepare changes separately from the shared branch. |
| `main` | The shared branch in this walkthrough. Some projects use another name. |
| Commit | A saved set of changes with an explanatory message. |
| Stage | Select changes to include in your next commit. |
| `origin` | The usual name for the GitHub repository connected to your local copy. |
| Push | Send your local commits to GitHub. |
| Pull request (PR) | A request to review your branch and add its changes to the shared branch. |
| Merge | Bring the approved changes into the shared branch. |

Creating a branch does not create an issue automatically. Pushing a branch
does not merge it. Merging a PR does not necessarily publish a software release.

## Before you start

**Contributor — GitHub and your terminal.**

You need Git installed, a GitHub account, authentication set up, and permission
to access the repository. See [Using Git and GitHub](github.md) for setup.
This walkthrough uses Git commands in a terminal and GitHub in a browser; the
GitHub CLI (`gh`) is optional and is not needed.

If you already have the project on your computer, open that folder in VS Code
and select **Terminal → New Terminal**. Otherwise, use the repository's **Code**
button to copy its clone URL, then run the following with your actual URL and
folder name:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

Run subsequent commands inside that project folder. Check your connection:

```bash
git remote -v
git status
```

**Expected outcome:** `origin` points to the intended GitHub repository, and
`git status` describes your local branch and files.

The main walkthrough assumes permission to push branches to the shared
repository. If you lack that permission, use the fork instructions below before
creating your branch.

## 1. Create an issue describing the work

**Contributor — GitHub in your browser.**

Open the repository and choose **Issues → New issue**. Use a supplied template
if there is one. For the example, enter:

```text
Title: Clarify installation instructions

Problem:
A new collaborator cannot tell which installation step to run first.

Proposed change:
Put the installation steps in order and explain the expected outcome.

Done when:
- The instructions can be followed from a fresh local copy.
- A reviewer has checked the commands and wording.
```

Submit the issue. Ask the maintainer to confirm the scope and who will do the
work. If the project requires an approved target version, record it here; a
release milestone can group issues planned for the same version. Follow the
project's policy before beginning implementation.

**Expected outcome:** an open issue with an agreed purpose and success criteria.
GitHub assigns a number, such as **#42**. Use your actual number below.

## 2. Create a branch from the latest main

**Contributor — your terminal.**

First run:

```bash
git status
```

Continue when it says `nothing to commit, working tree clean`. If it lists
unfinished changes, pause and save that work on its own branch or ask for help;
do not discard it to make this walkthrough work.

```bash
git switch main
git pull --ff-only origin main
git switch -c issue-42/installation-docs
git branch --show-current
```

The first two commands select and update your local `main`. The third creates
your working branch from it. The last prints the branch you are now using.
Use short descriptive names without spaces. If `main` has another name in your
project, substitute it throughout the guide.

**Expected outcome:** the last command prints `issue-42/installation-docs`.
Your branch exists locally; it will appear on GitHub after you push it.

## 3. Make and check your changes

**Contributor — your editor and terminal.**

Edit the relevant file in VS Code, then save it. For this example, improve the
installation section of `README.md`. Check the changes:

```bash
git status
git diff
```

`git status` lists changed files. `git diff` shows edits to files Git already
tracks; it does not show the contents of new, untracked files. Open those files
in your editor to inspect them. In a diff, `-` marks removed lines and `+` marks
added lines. If a long view opens, press `q` to leave it.

Run the project's relevant checks, using its README or contribution guide.
For documentation, preview the rendered page and verify the instructions.
For code, run the applicable tests and lint checks. Record the commands and
results for your PR. Ask the maintainer if the required checks are unclear.

**Expected outcome:** only the intended files have changed, and you have checked
that the change meets the issue's success criteria.

## 4. Save the change as a commit

**Contributor — your terminal.**

Stage the specific files you intend to include. Substitute your own file paths:

```bash
git add README.md
git diff --staged
git commit -m "Clarify installation instructions"
git status
```

`git diff --staged` shows exactly what the commit will contain. Review it before
running `git commit`. You can stage several named files in one command.
Selecting files explicitly helps keep unrelated work out of the PR.

If you staged a file by mistake, remove it from the next commit with:

```bash
git restore --staged README.md
```

This leaves your edits in place. Stage the correct files before committing.

**Expected outcome:** Git prints a commit identifier and your message. The
working tree is clean if you committed all intended edits. The commit is still
only on your computer.

## 5. Push your branch to GitHub

**Contributor — your terminal, then GitHub.**

```bash
git push -u origin issue-42/installation-docs
```

`-u` remembers where this branch should push in future. Open GitHub and select
your branch from the branch menu to check that your files and commit appear.

**Expected outcome:** your branch is on GitHub, and `main` has not changed.
If automated checks run on branch pushes, inspect their results. Checks may
instead run when you open the PR in the next step.

## 6. Open a pull request

**Contributor — GitHub in your browser.**

Choose **Compare & pull request** if GitHub shows that banner. Otherwise choose
**Pull requests → New pull request**. Confirm:

- **Base:** `main`, the destination for the change.
- **Compare:** `issue-42/installation-docs`, the branch containing your work.

Read the displayed changes before submitting. A simple description is:

```text
Title: Clarify installation instructions

What changed and why:
Put the installation steps in order and explain what each step produces.

How I checked it:
[Write the actual checks you ran and their results here.]

Closes #42
```

Use `Closes #42` only when the PR completes the issue. Use `Related to #42` if
more work will remain. Closing keywords automatically close a linked issue
when the PR is merged into the repository's default branch.
See [GitHub's issue-linking guide](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).

Select a reviewer where your permissions allow, or ask the maintainer in the
PR. Use a **draft pull request** if you want early feedback before the change
is ready. Mark it ready for review when your checks are complete.

**Expected outcome:** GitHub assigns the PR its own number. The issue number
and PR number need not match. The PR shows the proposed changes, discussion,
reviews and any configured automated checks.

## 7. Respond to review

**Reviewer and contributor — GitHub, your editor and terminal.**

The reviewer reads the changes and either approves them or requests changes.
Discuss unclear comments before editing. Make corrections on the same branch,
run the relevant checks again, then commit and push:

```bash
git branch --show-current
git add README.md
git commit -m "Address installation documentation review"
git push
```

Confirm the first command prints your issue branch. Replace the staged path
with the files you actually corrected. Reply to review comments with what you
changed and ask for another review when ready.

**Expected outcome:** the existing PR updates automatically. You do not need
another branch or another PR for review corrections.

## 8. Merge the approved pull request

**Maintainer — GitHub in your browser.**

Confirm the scope is complete, required reviews approve the latest changes,
and configured checks pass. If no checks are configured, verify the agreed
checks manually; their absence does not mean the change passed.

Use the repository's agreed merge method and confirm the merge. If GitHub
reports conflicts or blocks merging, resolve the reason rather than bypassing
the repository rules. See [GitHub's pull request guide](https://docs.github.com/en/pull-requests/get-started/pull-request-quickstart).

**Expected outcome:** the PR says **Merged**, the changes appear on `main`,
and the linked issue closes if the closing keyword applies. Recheck the issue's
success criteria before treating the work as complete.

## 9. Update your local copy

**Contributor — your terminal.**

Make sure `git status` shows no unfinished edits, then run:

```bash
git switch main
git pull --ff-only origin main
```

Open the changed file and confirm the merged change is present locally. The
maintainer or contributor can use GitHub's **Delete branch** button on the
merged PR to remove the remote working branch.

Optionally remove your local working branch:

```bash
git branch -d issue-42/installation-docs
```

If Git refuses, leave the branch in place and ask for help. Squash or rebase
merges can prevent Git from recognizing that the original branch was merged;
there is no need to force deletion to finish this walkthrough.

**Expected outcome:** your local `main` contains the reviewed change. Start the
next piece of work with a new issue and a new branch.

## If you cannot push to the shared repository

A **fork** is your own GitHub copy of a repository. Where repository policy
allows forks, click **Fork** on GitHub, clone your fork, and add the original
repository as `upstream`:

```bash
git clone https://github.com/YOUR-USERNAME/REPOSITORY.git
cd REPOSITORY
git remote add upstream https://github.com/OWNER/REPOSITORY.git
```

For step 2, with a clean working tree, use:

```bash
git switch main
git pull --ff-only upstream main
git switch -c issue-42/installation-docs
```

Follow the remaining editing, committing and pushing steps. `origin` now points
to your fork, so the push goes there. Open the issue in the original repository.
For the PR, choose the **original repository and its `main` branch** as the base,
and your **fork and issue branch** as the source. In step 9, use
`git pull --ff-only upstream main` instead of pulling from `origin`.

If forking is unavailable, ask an admin or maintainer how to contribute.

## If a step does not work

| What you see | What to do |
| --- | --- |
| Local changes before switching branches | Preserve that work first; do not discard it. |
| Branch name already exists | Check whether it is your existing issue branch; use `git switch` to resume it. |
| Commit asks for your name or email | Follow the identity setup in [Using Git and GitHub](github.md). |
| Push reports permission denied | Check authentication and access, or use the approved fork route. |
| `pull --ff-only` refuses to update | Your local and remote histories differ. Ask for help reconciling them. |
| GitHub reports a merge conflict | Ask the maintainer to help combine the overlapping changes. |
| No automated checks appear | Confirm which checks are required and whether automation is configured. |
| PR lists unrelated files | Review the staged files and branch starting point with the maintainer before merging. |

For a first practice run, choose a small documentation improvement with a
maintainer. Stop at the PR until someone has reviewed it, then verify the merged
result on GitHub and in your local copy.
