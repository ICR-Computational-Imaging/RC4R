# Semantic versioning with bumpversion

[Semantic Versioning](https://semver.org/spec/v2.0.0.html) gives releases a
*human-readable* version in the form `MAJOR.MINOR.PATCH`:

| Part | Increment when | Example |
| --- | --- | --- |
| `MAJOR` | A change is incompatible with the previous public interface | `1.4.2` → `2.0.0` |
| `MINOR` | Backwards-compatible functionality is added | `1.4.2` → `1.5.0` |
| `PATCH` | A backwards-compatible defect is fixed | `1.4.2` → `1.4.3` |

Versions beginning with `0`, such as `0.3.0`, normally describe initial
development: the public interface may still change substantially. Version
`1.0.0` marks the first stable public interface. Once a version has been
released, its contents should not be changed; publish a new version instead.

A version identifies a meaningful release, not an individual Git commit.
Normal development commits therefore do not each need a version bump.

## Development versions in this repository

This project combines semantic versioning principles with the
[Python packaging version format](https://packaging.python.org/en/latest/specifications/version-specifiers/#developmental-releases).
Work in progress uses a `.devN` suffix:

```text
0.1.0.dev1 < 0.1.0.dev2 < 0.1.0
```

The number after `dev` distinguishes successive development builds targeting
the same release. It is separate from the semantic `PATCH` number and does not
need to match the Git commit count.

The [development and release workflow](development_workflow.md) uses short-lived
issue branches created from `main`, with PRs targeting `main`. Each branch has
an approved issue and release-version target. Several issues may target the
same release; this does not require each branch to bump the package version.

Development suffixes identify preview builds when needed. A `.devN` version
does not imply a permanent branch named `dev`. A maintainer coordinates the
version change in release preparation, and stable release tags identify exact
reviewed commits on `main`. Branch names and version strings do not enforce
stability; tests, model verification, and review provide that evidence.

## What bumpversion updates

[bumpversion](https://github.com/peritus/bumpversion) applies a version change
consistently across the repository. Its configuration is stored in
`.bumpversion.cfg`.

For this project, a bump updates:

- `current_version` in `.bumpversion.cfg`.
- The package version recorded in `VERSION`.
- The version displayed in `site_name` in `mkdocs.yaml`.

The Python package reads `VERSION` through the configuration in
`pyproject.toml`, so its version does not need to be duplicated there.

The current configuration also creates a Git commit for each bump because
`commit = True`. It does not create a tag by default because `tag = False`.

## Previewing a change

Start from a clean working tree and preview the files and version that would be
changed:

```bash
bumpversion --dry-run --verbose build
```

A dry run does not modify files or create a commit. Review its output before
performing an important release bump.

## Creating a development build

Increment the development build number with:

```bash
bumpversion build
```

For example, this changes `0.1.0.dev4` to `0.1.0.dev5`. Because committing is
enabled in this repository, bumpversion updates the configured files and
creates a version-bump commit. Use this for a build that needs its own
identifiable version, rather than automatically running it after every commit.

## Creating a stable release

On an approved release-preparation branch, when the development version targets
the agreed release, remove its development suffix with:

```bash
bumpversion release
```

For example, `0.1.0.dev45` becomes `0.1.0`. This command updates the version
files and creates a commit. Push the branch and merge its reviewed PR into
`main` before creating the release tag. After updating local `main` and
confirming the intended version and commit:

```bash
git switch main
git pull --ff-only
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

Tagging after merge ensures the tag points to the reviewed commit on `main`,
including when GitHub squashes the PR. Do not create or push a release tag
until that commit and version are approved. Existing stable versions can use
an explicit new version as described below instead of removing a suffix.

## Setting an explicit version

When starting a new project from this template or moving to a deliberately
chosen release series, set the complete target version explicitly:

```bash
bumpversion --new-version 0.1.0.dev1 build
```

The final `build` argument is still required by bumpversion, even though
`--new-version` supplies the complete target. Preview the operation first:

```bash
bumpversion --dry-run --verbose --new-version 0.1.0.dev1 build
```

To update the files without creating bumpversion's automatic commit, add
`--no-commit`. This is useful when initialising a new project and combining the
version change with other template-renaming changes:

```bash
bumpversion --no-commit --new-version 0.1.0.dev1 build
```

## Example release sequence

For an approved release targeting `0.1.0`, with the current version
`0.1.0.dev45`:

1. Create a release-preparation branch from updated `main`, associated with
   the approved release issue.
2. Run `bumpversion release` on that branch to set `0.1.0`.
3. Run the required checks and obtain review, including model verification
   when the release changes model artifacts.
4. Merge the PR into `main`, update local `main`, and tag the exact reviewed
   commit as `v0.1.0`.
5. Publish the verified artifacts and package according to the release workflow.
6. Start subsequent work from updated `main` under a new approved issue. Set a
   development version only when an identifiable preview build is needed.

The next target is a project decision: use a patch version for a compatible
fix, a minor version for compatible functionality, or a major version for an
incompatible public-interface change.

## Common problems

### The working tree is dirty

bumpversion normally refuses to create a commit when unrelated changes are
present. Commit or stash those changes first. Avoid `--allow-dirty` for a real
release because it makes the contents of the version commit less clear.

### The configured version does not match a file

Do not update version strings in individual files manually. Ensure
`.bumpversion.cfg`, `VERSION`, and `mkdocs.yaml` all contain the current version,
then use bumpversion for subsequent changes.

### The version format is rejected

This repository's custom parser accepts stable versions such as `0.1.0` and
development versions such as `0.1.0.dev1`. Other suffixes require a deliberate
change to `.bumpversion.cfg` and should be tested with `--dry-run` first.

## Further reading

- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
- [Python packaging version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)
- [bumpversion documentation and command reference](https://github.com/peritus/bumpversion)
