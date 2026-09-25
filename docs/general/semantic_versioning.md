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

The intended branch convention is:

- The development branch contains versions such as `0.1.0.dev45`.
- The main branch contains stable releases such as `0.1.0`.
- After releasing `0.1.0`, development can begin on `0.2.0.dev1` or whichever
  release is planned next.

Branch names do not enforce stability by themselves. Tests, review, and the
release workflow determine whether a version is ready for the main branch.

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

When the development version has passed its tests and is ready to release,
remove its development suffix with:

```bash
bumpversion release
```

For example, `0.1.0.dev45` becomes `0.1.0`. To create an annotated Git tag at
the same time, override the repository's default for this command:

```bash
bumpversion --tag release
```

This produces a tag such as `v0.1.0`. Push the release commit and tag only
after verifying them:

```bash
git push origin main
git push origin v0.1.0
```

Do not run the push commands until the release commit has been merged onto the
main branch and `v0.1.0` is the intended public release.

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

For a development branch currently at `0.1.0.dev45`:

1. Ensure the working tree is clean and all tests pass.
2. Merge the tested release candidate according to the project's branch
   policy.
3. Run `bumpversion --tag release` on the release branch to create `0.1.0`.
4. Verify the version, commit, and tag before pushing them.
5. Begin the next planned release on the development branch, for example with
   `bumpversion --new-version 0.2.0.dev1 build`.

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
