# Development and release workflow: a walkthrough

![Overview of the development and release workflow](../assets/development-workflow.svg)

Use this guide to take a change from an idea to a reviewed contribution and,
later, a software release. The sequence is **issue → approved plan → branch →
changes and checks → pull request → review and merge → release preparation →
tag and publication**. Contributors normally finish at step 8; maintainers
continue with steps 9–10 when a release is ready.

The example is issue **#42**, “Clarify installation instructions”, targeting
version **0.1.0**. Replace `OWNER`, `REPOSITORY`, issue numbers, branch names,
file paths, and versions with your own. Commands are examples to run at the
appropriate step, not a script to execute all at once.

## Who does what?

| Role | Responsibility |
| --- | --- |
| Admin | Grants access, configures repository rules, and manages publishing credentials and approval settings. |
| Maintainer | Approves the scope and target version, assigns reviewers, merges approved changes, and prepares and publishes releases. |
| Contributor | Raises an issue, makes changes on a branch, runs checks, opens a PR, and responds to review. |
| Reviewer | Checks the proposed changes and evidence, then approves or requests corrections. |
| User | Installs or uses a published release and reports problems through issues. |

One person may hold several roles. GitHub permissions determine what someone
can do; the team agrees who is responsible for doing it. GitHub Actions runs
the configured checks but does not replace human review.

## How GitHub permissions are assigned

**Responsible: repository owner or admin. Location: GitHub repository settings.**

The roles above describe project responsibilities. GitHub permissions determine
which actions a person can actually perform.

### Who owns the repository?

The owner is the account shown before the repository name in
`github.com/OWNER/REPOSITORY`:

- **Personal account:** a repository created under your account belongs to you.
  GitHub has two permission levels here: owner and collaborator. Invited
  collaborators receive write access; there are no separate repository
  **Maintain** or **Admin** roles to assign.
- **Organisation account:** the organisation owns the repository, even when an
  individual creates it. Organisation owners and repository admins manage its
  access. People or teams can receive **Read**, **Triage**, **Write**, **Maintain**,
  or **Admin** permissions.

Ownership can be transferred, so the original creator is not always the current
owner. See [personal repository permissions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)
and [organisation repository roles](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization).

### Invite people and assign access

For an organisation repository:

1. Open **Settings → Collaborators & teams**.
2. Choose **Add people** or **Add teams**, and select the GitHub account or team.
3. Choose the repository role, then confirm. A newly invited person accepts the
   invitation to gain access.
4. Review the access list and its **Role** dropdown when changing responsibilities
   or removing access.

A useful starting mapping is:

| Project responsibility | Organisation repository permission |
| --- | --- |
| User | Public access, or **Read** for a private repository. |
| Contributor | **Write** to push branches; a fork may be used without write access. |
| Maintainer | **Maintain** for day-to-day repository management. |
| Admin | **Admin** to manage access and repository settings. |

For a personal repository, use **Settings → Collaborators → Add people** to
invite collaborators. Agree contributor and maintainer responsibilities within
the team; they share GitHub's collaborator permission level. See
[GitHub's access-management instructions](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-teams-and-people-with-access-to-your-repository).

Repository roles alone do not reserve merging for maintainers. Configure
[branch rules](#repository-setup-make-the-rules-enforceable) and required
reviews to enforce the team's process, and publishing
environment approvals where needed. Access to external data stores and package
registries is managed separately from GitHub repository permissions.

**Expected result:** the access list records each person or team's technical
permissions, while this guide and the README identify their project responsibilities.

## A few terms before you start

**Git** records changes on your computer. **GitHub** holds the shared copy online.
Your computer's copy is *local*; the GitHub copy is *remote*.

| Term | Meaning |
| --- | --- |
| Repository | The project files and their recorded history, often called a “repo”. |
| Issue | A numbered discussion describing a problem or planned improvement. |
| Branch | A named line of work where you prepare changes separately from the shared branch. |
| `main` | The shared branch in this guide; substitute your project's name if different. |
| Stage | Select changes to include in the next commit. |
| Commit | A saved set of changes with an explanatory message. |
| `origin` | The usual name for the GitHub repository connected to your local copy. |
| Push | Send local commits or tags to GitHub. |
| Pull | Bring changes from GitHub into your local branch. |
| Pull request (PR) | Ask someone to review your branch and add its changes to another branch. |
| Merge | Bring approved changes into the destination branch. |
| Tag | A name such as `v0.1.0` pointing to one specific commit. Treat release tags as fixed. |
| Release | A published version with release notes and any approved downloadable files. |

Creating a branch does not create an issue. Pushing a branch does not merge
it. Merging a PR does not necessarily publish a release.

## Before the walkthrough

**Responsible: contributor; admin grants access and maintainer helps with setup.**
**Location: your terminal and GitHub.**

Install Git, create a GitHub account, and set up authentication using the
[GitHub setup guide](https://docs.github.com/en/get-started/git-basics/set-up-git).
This walkthrough uses Git in a terminal and GitHub in a browser. GitHub CLI
(`gh`) is optional; only the optional publication example uses it.

If you do not already have a local copy, use the repository's **Code** button
to copy its clone URL. Substitute that URL and the actual folder name below:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

If you already have a copy, open a terminal in that project folder. Run the
remaining commands there unless a step explicitly changes folders. Check:

```bash
git remote -v
git status
```

**Expected result:** `origin` points to the intended repository and `git status`
shows your local branch and any unfinished changes. Do not type explanatory
output shown in separate text blocks.

The main walkthrough assumes you can push branches to the shared repository.
If you cannot, use the [fork instructions](#if-you-cannot-push-to-the-shared-repository)
before creating your branch.

Automated checks and access restrictions must be configured by the team.
No checks appearing on GitHub does not mean the change has passed testing.

## 1. Describe the work in an issue

**Responsible: contributor. Location: GitHub in your browser.**

Open the repository and choose **Issues → New issue**. Use the supplied
template if there is one. For this example:

```text
Title: Clarify installation instructions

Problem:
A new collaborator cannot tell which installation step to run first.

Proposed change:
Put the installation steps in order and explain their expected outcomes.

Done when:
- The instructions work from a fresh local copy.
- A reviewer has checked the commands and wording.

Proposed target version: 0.1.0
```

Create an issue for every working branch, including documentation changes
and release preparation. The issue states the purpose and success criteria;
it is not a request to merge code yet.

**Expected result:** GitHub assigns an issue number, such as **#42**.
Use your actual number in the branch name and PR below.

## 2. Agree the scope and target version

**Responsible: maintainer. Location: the GitHub issue.**

Review the proposed work, agree how it will be checked, and confirm the target
release before implementation begins. Leave an explicit comment, for example:

```text
Approved: clarify the installation steps and check them from a fresh checkout.
Target release: 0.1.0.
```

Assign the issue to a [milestone](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones)
such as `v0.1.0` if useful. A milestone groups work planned for a release; the comment records approval.
Several issues may share a target version. The contributor does not need to change version files
on every issue branch.

Versions usually follow `MAJOR.MINOR.PATCH`. For a stable public API, compatible
fixes change PATCH, compatible features change MINOR, and incompatible changes
change MAJOR. The maintainer should also explain expectations for early `0.x`
releases, which can change more freely. See [Semantic Versioning](semantic_versioning.md).

**Expected result:** contributor and reviewer know the agreed scope, required
checks, and target version. Agree any later change to that plan with the maintainer.

## 3. Start your branch from main

**Responsible: contributor. Location: your terminal.**

First check for unfinished work:

```bash
git status
```

Continue when it says `nothing to commit, working tree clean`. If files have
unfinished changes, save them on their own branch or ask for help; do not
discard them to make this walkthrough work.

Update your local `main`, then create the issue branch:

```bash
git switch main
git pull --ff-only origin main
git switch -c issue-42/installation-docs
git branch --show-current
```

The first command selects local `main`. The second updates it from GitHub
without creating a merge commit. The third creates and selects your working
branch. The last confirms which branch you are using.

**Expected output from the last command:**

```text
issue-42/installation-docs
```

This branch exists locally. It appears on GitHub after you push it in step 6.
If `pull --ff-only` refuses to update, your local and remote histories differ;
ask for help reconciling them before starting the new branch.

## How the branches fit together

![An issue branch and a release branch merging into main before tagging](../assets/development-branches.svg)

An issue branch starts from a commit on `main`. You add commits there while
other contributors work on their own branches. Review brings the approved
change back into `main`. Release preparation later follows the same pattern,
and the release tag points to the resulting approved commit on `main`.

This guide uses short-lived issue branches. A permanent `dev` branch is
optional: it can help a team integrate related changes before they are ready
for `main`, but several contributors alone do not require it. If your team
uses `dev`, agree the PR destination and promotion rules with the maintainer
rather than switching the base branch halfway through a change.

## 4. Make the change and test it

**Responsible: contributor; maintainer identifies required checks.**
**Location: your editor and terminal.**

For the example, improve the installation section of `README.md`. Keep the
change within the agreed issue. For code changes, update relevant tests and
explanations alongside the code.

Review the edits:

```bash
git status
git diff
```

`git status` lists changed files. `git diff` shows unstaged edits to files Git
already tracks: `-` marks removed lines and `+` marks added lines. It does not
show the contents of new, untracked files; open those in your editor. Press
`q` if needed to leave Git's displayed diff.

Follow the project's README for environment setup and checks. For this
example, check the installation instructions in a fresh environment and
preview the Markdown. A Python project using uv, pytest, Ruff, and MkDocs
(such as this one!) might also use the following.
These tools are examples, not prerequisites for using Git:

```bash
uv sync --locked
uv run --locked pytest
uv run --locked ruff check .
uv run --locked mkdocs build --strict
```

| Check | Expected result |
| --- | --- |
| Tests, such as `pytest` | Relevant tests pass. |
| Lint, such as `ruff check` | No issues covered by the configured lint rules. Formatting may need a separate check. |
| Documentation preview/build | Pages render correctly and instructions match the change. |
| Other agreed checks | Type checks, builds, or integration checks pass when required by the project. |

Use the actual dependencies and commands agreed for your project. Record
which checks you ran and their results. If a check fails, read its output and
fix the cause or report the problem to the maintainer.

**Expected result:** only the intended changes are present and the agreed
checks pass. These checks support the issue's success criteria.

## 5. Save your work in a commit

**Responsible: contributor. Location: your terminal.**

Stage the specific files that belong to this change. For the example:

```bash
git add README.md
git diff --staged
git commit -m "Clarify installation instructions"
git status
```

`git add` selects changes for the next commit. `git diff --staged` shows exactly
what will be included; review it before committing. `git commit` saves those
changes locally. Stage any other intended files explicitly rather than
including unrelated work.

If you staged a file by mistake, remove it from the next commit while keeping
its edits:

```bash
git restore --staged README.md
```

**Expected result:** Git prints a commit identifier and your message. The
working tree is clean if you committed all intended edits. The commit is
still only on your computer. Several focused commits can belong to one issue.

## 6. Push the branch and check the GitHub results

**Responsible: contributor; GitHub Actions runs any configured checks.**
**Location: your terminal, then GitHub.**

Send the branch to GitHub for the first time:

```bash
git push -u origin issue-42/installation-docs
```

`-u` remembers which remote branch goes with this local branch. After later
commits on the same branch, use `git push`.

If this change includes DVC-managed data or model outputs, also follow
[uploading DVC artifacts](#upload-dvc-artifacts-for-review) below before asking
reviewers to retrieve them. `git push` sends the tracking files and commits;
`dvc push` sends the associated artifact contents to their configured storage.

On GitHub, select your branch to confirm the files and commit are present.
Open **Actions** and inspect the run for the latest commit if branch checks
are configured. Some projects run checks only when a PR opens. For failed
checks, read the logs, correct the problem locally, check, commit, and push.

**Expected result:** your branch and commits are on GitHub; `main` has not
changed. The applicable automated checks pass. If no checks appear, ask the
maintainer which checks are required and how they are verified.

## 7. Open a pull request to main

**Responsible: contributor. Location: GitHub in your browser.**

Choose **Compare & pull request** if GitHub shows it. Otherwise choose
**Pull requests → New pull request**. Confirm:

- **Base:** `main`, the destination for the change.
- **Compare:** `issue-42/installation-docs`, the branch containing your work.

Read the displayed changes before submitting. A useful description is:

```text
Title: Clarify installation instructions

What changed and why:
Put installation steps in order and explain the expected outcomes.

How I checked it:
[Describe the actual checks you ran and their results.]

Target release: 0.1.0, approved in issue #42.
Closes #42
```

Only claim checks that passed. `Closes #42` links and automatically closes
the issue when the PR merges into the default branch. Use `Related to #42`
if work will remain. See [GitHub's issue-linking guide](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue).

Request a reviewer where your permissions allow, or ask the maintainer in the
PR. Use a **draft PR** for early feedback; mark it ready for review once your
checks are complete.

**Expected result:** the PR has its own number, which need not match the issue
number. It displays the changes, discussion, reviews, and configured checks.
Opening the PR requests review; it does not merge your work.

## 8. Review, update, and merge

### Review the change

**Responsible: reviewer. Location: GitHub.**

Read the changes against the issue's success criteria and check the evidence
for the latest commit. Approve or request specific corrections. An approval
is a review decision; the maintainer still decides when the change can merge.

### Address corrections and conflicts

**Responsible: contributor; reviewer checks the updated work.**
**Location: your issue branch and GitHub.**

Make corrections on the same branch, rerun the relevant checks, then commit
and push:

```bash
git branch --show-current
git add README.md
git diff --staged
git commit -m "Address installation documentation review"
git push
```

Confirm that the first command prints your issue branch. Substitute the files
you corrected. Reply to review comments and request another review. The
existing PR updates automatically; no new branch or PR is needed.

If GitHub requires the branch to be updated with `main`, start from a clean
working tree on your issue branch:

```bash
git fetch origin
git merge origin/main
```

Resolve any conflicts with the maintainer's help if needed. Complete the merge
commit when Git requests it, then rerun checks and push. Changes after review
need current checks and any fresh approval required by the repository.

### Merge the approved pull request

**Responsible: maintainer. Location: GitHub.**

Confirm the scope is complete, required reviews approve the latest work, and
required checks pass. If no automated checks are configured, verify the agreed
checks manually. Use the project's agreed merge method and confirm the merge.
Resolve blocked checks or conflicts rather than bypassing repository rules.

**Expected result:** the PR says **Merged**, its changes appear on `main`, and
the linked issue closes when the closing keyword applies. Confirm the issue's
success criteria have been met before treating the work as complete.

### Update your local copy

**Responsible: contributor. Location: your terminal.**

With no unfinished edits:

```bash
git switch main
git pull --ff-only origin main
```

Open the changed file and confirm the reviewed result is present. The
maintainer or contributor can use **Delete branch** on the merged PR to remove
the remote working branch. Optionally remove your local branch:

```bash
git branch -d issue-42/installation-docs
```

If Git refuses, keep the branch and ask for help. Squash and rebase merges can
make Git unable to recognise the original branch as merged; force deletion is
not needed to finish this walkthrough.

**Expected result:** your local `main` contains the merged change. Start the
next piece of work with a new issue and branch. Release preparation is a
separate task, usually covering several merged issues.

## 9. Prepare a release when the agreed work is ready

**Responsible: maintainer prepares the release; reviewer checks it; admin maintains publishing access.**
**Location: GitHub, your editor, and your terminal.**

Create an approved release issue, such as **#57**, and start a release branch
from a clean, updated `main`:

```bash
git switch main
git pull --ff-only origin main
git switch -c issue-57/release-0.1.0
```

Agree the version, list the included changes in the release notes, and check
that completed issues match the release scope. Update the configured version
files together using the project's agreed version tool.

Use [bumpversion](semantic_versioning.md), which is included in the development dependencies.
Start from a clean working tree and choose **one** command for the approved change:

| Change | Command | When to use it |
| --- | --- | --- |
| MAJOR | `uv run bumpversion major` | An incompatible change to the public interface. |
| MINOR | `uv run bumpversion minor` | New functionality compatible with the previous interface. |
| PATCH | `uv run bumpversion patch` | A compatible bug fix. |

For example, preview a minor bump before applying it:

```bash
uv run bumpversion --dry-run --verbose minor
uv run bumpversion minor
```

The preview does not change files. The second command applies the version
change and creates a commit if `commit = True`. Keep `tag = False` so the
maintainer creates the release tag only after review and merge. Configuration
and development-suffix handling are explained in the linked versioning guide.

If a dependency lockfile records the project version, refresh it using the
project's normal command, such as `uv lock`, and commit the update.

If the release includes model artifacts, follow
[Prepare a model release](../dermapred/model_download.md#prepare-a-release)
after setting the final release version and before reviewing the release PR.
The contributor prepares the manifest for the selected weights and matching
calibrator, the reviewer verifies those files, and the maintainer confirms
that they may be distributed publicly. Include the manifest in the release PR
and make the private artifacts available for review using the
[DVC upload step](#upload-dvc-artifacts-for-review), where applicable.
Keep those exact files for the later GitHub upload; generating the manifest
does not upload them.

Run the agreed release checks, including installation from a built package
when applicable. Push the release branch and open a PR using steps 6–8.
Review covers the version, notes, code, and any selected release assets.

**Expected result:** the reviewed release-preparation PR is merged into `main`.
The version files identify the intended release. The maintainer creates the
release tag only in the next step.

## 10. Tag the reviewed commit, then publish

### Create and push the release tag

**Responsible: maintainer. Location: your terminal, then GitHub.**

Copy the resulting commit identifier from the merged release PR. A squash or
rebase merge can produce a different identifier from the original branch
commit. Use the resulting approved commit on `main`.

Update the local history and confirm the release version at that commit:

```bash
git switch main
git pull --ff-only origin main
git log --oneline -5
git show APPROVED_COMMIT_SHA:VERSION
```

Replace `APPROVED_COMMIT_SHA` with the actual identifier. If the project stores
its version elsewhere, inspect that version file instead. A release version
of `0.1.0` should correspond to tag `v0.1.0` under this naming convention.

Create an annotated tag, inspect it, then push that specific tag:

```bash
git tag -a v0.1.0 APPROVED_COMMIT_SHA -m "Release 0.1.0"
git show --no-patch v0.1.0
git push origin v0.1.0
```

The commit identifier prevents accidentally tagging newer work that reached
`main` after the release PR. Do not move an already published release tag;
prepare a new version for later corrections.

**Expected result:** GitHub lists `v0.1.0` under **Tags**, pointing to the approved
commit. A tag labels code; it does not itself create a GitHub Release or upload
a package unless the team has configured automation to do so.

### Upload model artifacts to GitHub, when applicable

**Responsible: maintainer uploads the approved files; reviewer checks the draft.**
**Location: your terminal, then GitHub Releases.**

After the release PR has merged and its matching tag has been pushed, follow
[Upload the files to a draft GitHub Release](../dermapred/model_download.md#upload-the-files-to-a-draft-github-release).
That guide covers authentication, a local dry run, the upload command, and
verification of the uploaded attachments. Use the manifest reviewed in step 9
and the same selected files, without retraining or refitting calibration.

This is the step that sends the model artifacts to GitHub. A DVC push stores
artifacts in the configured data remote; the package-publishing workflow
uploads code distributions to the package registry. Neither performs this
GitHub Release upload.

**Expected result:** the existing release tag has a draft GitHub Release
containing the verified weights, matching calibrator, and reviewed manifest.
The maintainer publishes that draft after its notes and attachments are approved.

### Publish and check the release

**Responsible: maintainer; configured release reviewer approves publication; admin manages credentials.**
**Location: GitHub and the chosen package registry or deployment service.**

Use the project's agreed publishing process. For a GitHub Release, open
**Releases → Draft a new release**, select the existing `v0.1.0` tag, review the
notes and approved attachments, then publish when authorised.
If the model-upload step already created a draft, open and review that draft
rather than creating another release. Publish its approved artifacts and
verify their public downloads and inference behaviour before publishing a
package release that depends on them. The
[model-release guide](../dermapred/model_download.md#download-a-model)
describes the download checks; the
[package-publishing walkthrough](publishing_to_pypi.md) covers TestPyPI and PyPI.


For package publication, build from the tagged code and check that the installed
package works in a fresh environment. A separate checkout avoids accidentally
building later changes from `main`:

```bash
git worktree add --detach ../release-check-0.1.0 v0.1.0
cd ../release-check-0.1.0
```

For a Python project using uv, `uv build` creates a wheel and source archive in
`dist/`. Check installation using the actual wheel filename and the project's
normal import or command. A successful import is one check; also verify the
expected user behaviour. Keep older distributions out of the upload directory.

If the project has a manually triggered workflow named `publish.yaml` with a
`registry` input, the maintainer can test publication with GitHub CLI:

```bash
gh workflow run publish.yaml --ref v0.1.0 -f registry=testpypi
```

This command is an example for that workflow design, not a built-in GitHub
publication command. It requires the workflow on the default branch, the
matching tagged version, and configured credentials. After verifying the
TestPyPI installation, run the same reviewed tag for production:

```bash
gh workflow run publish.yaml --ref v0.1.0 -f registry=pypi
```

The admin configures the publishing environments and secrets; reviewers
approve the jobs if required by those environments. For a Python package
using API tokens, PyPI and TestPyPI need separate tokens. An environment secret
such as `PYPI_API_TOKEN` can hold the matching token in each environment.
See [PyPI's API-token guidance](https://pypi.org/help/#apitoken) and
[GitHub's environment-secret instructions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

**Expected result:** users can obtain the published version and its release
notes, and the released files match the reviewed tag. Confirm the registry
version and test the normal installation or usage instructions before closing
the release issue. Publication is separate from merging and tagging.

## If you cannot push to the shared repository

**Responsible: contributor; admin or maintainer confirms the permitted contribution route.**
**Location: GitHub and your terminal.**

A **fork** is your own GitHub copy of a repository. Where project policy allows
forks, choose **Fork**, then clone your copy and connect the original repository
as `upstream`:

```bash
git clone https://github.com/YOUR-USERNAME/REPOSITORY.git
cd REPOSITORY
git remote add upstream https://github.com/OWNER/REPOSITORY.git
```

Open the issue in the original repository. In step 3, update from `upstream`
before creating your issue branch:

```bash
git switch main
git pull --ff-only upstream main
git switch -c issue-42/installation-docs
```

Follow the editing, checking, and committing steps. Push to `origin`, which
now points to your fork. For the PR, choose the **original repository and its
`main` branch** as the base, and your **fork and issue branch** as the source.
In step 8, update your local `main` using `git pull --ff-only upstream main`.
Release tagging and publication remain the maintainer's responsibility in the
original repository. If forks are unavailable, ask how to contribute.

## Extra checks for releases with data or model files

**Responsible: contributor prepares evidence; reviewer verifies it; maintainer approves the selected files; admin controls access.**

These checks are optional for projects without such assets. Keep restricted
data and large model files out of ordinary code commits. Use the project's
approved storage and access arrangements; unit tests should use synthetic or
otherwise approved fixtures where private data are unavailable.

Before release, identify the exact selected files, their licence, source code
version, required preprocessing, and verification results. A manifest can
record download URLs, sizes, and hashes. It describes files but does not upload
them or prove their performance.

| Role | Release check |
| --- | --- |
| Contributor | Records provenance and the exact candidate files, with hashes and relevant results. |
| Reviewer | Confirms file identity and compatibility with the proposed software. |
| Maintainer | Confirms the agreed verification passed and public distribution is authorised. |
| Admin | Maintains storage permissions and any restricted verification or upload credentials. |

Upload the approved bytes without retraining or replacing them after review.
Check the public download, integrity verification, and normal usage before
publishing the final release. Changed files need fresh verification. Keep
private evaluation reports private unless their publication is approved.

### Upload DVC artifacts for review

**Responsible: contributor with storage write access; otherwise an authorised maintainer uploads them.**
**Location: your terminal and the configured DVC remote.**

This step applies only to projects using DVC. Complete it when a change
introduces or updates tracked datasets or pipeline outputs, before the PR is
ready for artifact review. Reviewers need both the Git tracking files and the
corresponding cached files in the remote; committing a lockfile alone does not
make the model or data available to them.

1. Check the selected pipeline. Reproduce it if its inputs or outputs are out
   of date, then review the generated tracking changes:

   ```bash
   dvc status dvc.yaml
   dvc repro dvc.yaml
   ```

   `dvc.yaml` is an example pipeline target; substitute the intended pipeline
   path. Reproduction runs commands when needed; status only reports changes.
   Do not run a separate held-out evaluation pipeline merely to prepare a PR.

2. Upload the selected pipeline's cached outputs:

   ```bash
   dvc push dvc.yaml
   ```

   This includes declared cached outputs such as model files, processed data,
   or plots. For source datasets tracked with `dvc add`, also target their
   `.dvc` files when those datasets need uploading. For example, replace the
   dataset path below with the actual tracking file:

   ```bash
   dvc push path/to/dataset.dvc dvc.yaml
   ```

   Use explicit targets when the repository contains pipelines or datasets
   with different access requirements. Untargeted `dvc push` and `dvc pull`
   include tracked artifacts across the repository, including held-out test
   data if those data are tracked. A default training remote does not filter
   out test data: the targets select the files, while saved remote assignments
   or the default select their storage destination. Target the intended
   pipeline and dataset `.dvc` files to avoid transferring other datasets or
   contacting a remote you cannot access. Files declared with `cache: false`
   are not uploaded to a DVC remote; keep their contents in Git.

3. Review and commit the changed pipeline definitions, lockfile, dataset
   `.dvc` files, and generated ignore files, following step 5. For example:

   ```bash
   git add dvc.yaml dvc.lock
   git diff --staged
   git commit -m "Update pipeline artifact versions"
   git push
   ```

   Stage any changed dataset tracking and ignore files explicitly too. Use
   `git push -u origin YOUR-BRANCH` for a branch's first push, as in step 6.
   Keep cached artifact contents out of Git. If the tracking changes were
   already committed, upload the artifacts and push those existing commits;
   another commit is not needed solely because `dvc push` ran.

For a uv-managed project with DVC installed in a `train` dependency group,
prefix the DVC commands accordingly, for example:

```bash
uv run --group train dvc push dvc.yaml
```

In the PR description, identify the pipeline or dataset targets, the relevant
checks, and whether their artifacts have been uploaded. After checking out the
PR commit, an authorised reviewer can retrieve the same pipeline outputs with
`dvc pull dvc.yaml`; raw datasets may need their own `.dvc` targets too.

**Expected result:** the PR identifies the exact artifact versions, and reviewers
with storage access can retrieve them. Uploading to the configured DVC remote
is separate from publishing approved files on a GitHub Release or uploading
the Python package to PyPI. See [DVC push documentation](https://doc.dvc.org/command-reference/push).

## Repository setup: make the rules enforceable

**Responsible: admin configures access and rules; maintainer specifies required checks and reviewers.**
**Location: GitHub repository settings and workflow files.**

Require PRs, passing checks, and the agreed approval before changes enter
`main`. Decide who can merge or bypass rules, and protect release tags where
needed. Configure publishing environments, required reviewers where supported,
and access to release credentials. See [GitHub's branch protection guide](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

Configure the project's checks for branch pushes and PRs. If issue links and
approved target versions must be enforced automatically, add checks for them.
A branch name, milestone, or written policy does not configure GitHub rules.
Missing checks are not evidence of success. Do not expose publishing or
restricted-data credentials to untrusted PR jobs.

### Protecting the main branch

**Responsible: admin configures the rules; maintainer agrees required checks and reviewers.**
**Location: GitHub repository settings.**

`main` is the shared starting point for new work and release preparation.
Protection makes review and testing requirements enforceable: contributors
cannot bypass the PR process by pushing changes directly to `main`. It also
protects the branch from deletion and force pushes that could rewrite shared
history. Changes retain their PR discussion, review, and test evidence, giving
the team a dependable basis for subsequent work and releases.

Create a branch ruleset:

1. Open **Settings → Rules → Rulesets** in the repository.
2. Select **New ruleset → New branch ruleset**.
3. Name it `Protect main`.
4. Set **Enforcement status** to **Active**. A disabled ruleset does not enforce
   the requirements.
5. Under **Target branches**, choose **Add target → Include by pattern** and
   enter `main`. Substitute your shared branch name if it differs.
6. Leave the **Bypass list** empty so the rules apply to contributors,
   maintainers, and admins alike.
7. Select the protections below and save the ruleset.

| Setting | Suggested value | Purpose |
| --- | --- | --- |
| Require a pull request before merging | Enabled | Changes enter through a reviewable PR. |
| Required approvals | `1` | Another person reviews the change before merge. |
| Dismiss stale approvals when new commits are pushed | Enabled | Earlier approval does not cover later edits automatically. |
| Require conversation resolution before merging | Enabled | Outstanding review discussions are addressed. |
| Require status checks to pass | Enabled | The agreed automated checks must succeed. |
| Require branches to be up to date before merging (under status checks) | Enabled | Checks cover the proposed change with the latest `main`. |
| Block force pushes | Enabled | Shared branch history cannot be rewritten by a force push. |
| Restrict deletions | Enabled | The protected branch cannot be deleted through ordinary branch operations. |

First enable **Require status checks to pass**. In that rule's expanded
**Additional settings**, enable **Require branches to be up to date before
merging**; this is not a separate top-level rule. Add at least one required
status check for the setting to take effect.

#### Find the check names in the workflow

**Responsible: maintainer identifies the checks; admin adds them to the ruleset.**

On GitHub, open the repository's **Code** tab, then `.github/workflows/` and
its test workflow file. A common filename is `tests.yaml`; use your project's
actual filename. The workflow's top-level `name` identifies it in the **Actions**
tab. The `name` under a job identifies that job's status check.

For example, this excerpt defines a workflow named **Unit tests** with two
Python test jobs:

```yaml
name: Unit tests

jobs:
  tests:
    name: Pytest (Python ${{ matrix.python-version }})
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
```

GitHub replaces the matrix expression with each Python version, producing
**Pytest (Python 3.11)** and **Pytest (Python 3.12)**. Select those job names
as required status checks; `Unit tests` is the workflow name and `tests` is
its internal job identifier, not the two check names.

To confirm the names and configure them:

1. Push a working branch or open a PR, as in
   [step 6](#6-push-the-branch-and-check-the-github-results) and
   [step 7](#7-open-a-pull-request-to-main), so the configured workflow runs.
2. Open **Actions → Unit tests → the run for that commit**, or the PR's
   **Checks** tab. Confirm the actual job names and results.
3. Return to **Settings → Rules → Rulesets → Protect main** and add the
   agreed jobs under **Require status checks to pass**. Require both Python
   jobs if both are part of the project's agreed checks, then save.

No checks are required by default. The workflow file defines **how checks run**;
the ruleset defines **which checks must pass before merging**. Enabling the
rule without adding checks does not select them automatically. If the selector
is empty, let the test workflow run on GitHub first, then return and confirm
the check names. Once configured, these checks become enforceable requirements
for the maintainer's merge in [step 8](#8-review-update-and-merge).

One required approval means the PR author needs another reviewer; they cannot
approve their own PR. Agree who provides that review before enforcing the rule.
Repository **Write** or **Maintain** permissions alone do not restrict merging
to one named maintainer, so any additional merge-access policy must also be
configured deliberately.

**Expected result:** a PR targeting `main` cannot merge until its required
checks, review, and conversation requirements are satisfied. Contributors
continue to push their working branches normally. Package publication remains
controlled separately by the publishing workflow and its environment settings.

See [GitHub's ruleset setup instructions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository)
and [available protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

## If a step does not work

**Responsible: contributor reports the problem; maintainer or admin helps resolve it.**

| What you see | What to do |
| --- | --- |
| Local changes before switching branches | Save the work on its own branch; do not discard it. |
| Branch name already exists | Confirm it is your issue branch, then use `git switch` to resume it. |
| Commit asks for your name or email | Configure Git identity using the setup guide linked above. |
| Push reports permission denied | Check authentication and access, or use the approved fork route. |
| `pull --ff-only` refuses to update | Ask for help reconciling local and remote history. |
| GitHub reports merge conflicts | Resolve the overlapping changes with help, rerun checks, and push. |
| No automated checks appear | Ask which checks are required and whether automation is configured. |
| PR lists unrelated files | Review the branch starting point and staged files before merging. |
| Release tag does not match the package version | Check the version at the approved commit before creating or using a tag. |
| Publication waits for approval | The configured release reviewer must approve the environment job. |

For a first practice run, agree a small documentation change with a maintainer
and follow steps 1–8. Check both the merged result on GitHub and your updated
local copy. Release work in steps 9–10 happens when the maintainer agrees it is ready.

## Copy this guide to another project

**Responsible: maintainer or documentation contributor.**

Copy this file and `development-workflow.svg` and `development-branches.svg`.
Keep the figures in the relative `../assets/` location or update the two image
paths. The numbered steps match the figures. Replace the example repository,
issue numbers, versions, and optional tool commands as needed; no other local
documentation pages or project-specific scripts are required for the core Git
walkthrough. When reusing the optional release steps, update the model-release
and package-publishing links to your project's equivalent guides.
