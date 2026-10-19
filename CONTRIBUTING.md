# Contributing

The [development and release workflow](docs/development_workflow.md) contains
the full walkthrough, commands, figures, responsibilities, and expected outcomes.

## Make a contribution

1. **Contributor:** [raise an issue](docs/development_workflow.md#1-describe-the-work-in-an-issue)
   describing the problem, proposed change, and how completion will be checked.
   Every working branch needs an associated issue, including documentation changes.
2. **Maintainer:** [approve the scope and target release](docs/development_workflow.md#2-agree-the-scope-and-target-version)
   before implementation begins.
3. **Contributor:** [create an issue branch from updated main](docs/development_workflow.md#3-start-your-branch-from-main)
   and set the approved development version if it is not already set.
   [Make the changes and run the required checks](docs/development_workflow.md#4-make-the-change-and-test-it).
4. **Contributor:** push the branch and [open a pull request](docs/development_workflow.md#7-open-a-pull-request-to-main),
   linking the issue and explaining the changes and checks performed.
5. **Reviewer:** [check the changes and functionality](docs/development_workflow.md#8-review-update-and-merge).
   The contributor addresses feedback; the maintainer merges after the agreed
   checks and review pass. Submit changes through a PR rather than pushing directly to `main`.

## Versioning and releases

Contributors keep their branches on the approved development version, such as
`0.1.1.dev0`. Do not increment the target again if it is already set, and
**do not run `bumpversion release`** or remove the development suffix manually.

The maintainer [prepares the stable release](docs/development_workflow.md#9-prepare-a-release-when-the-agreed-work-is-ready)
through a reviewed PR, then [tags the approved merged commit and publishes](docs/development_workflow.md#10-tag-the-reviewed-commit-then-publish).
See the workflow for release checks, artifact verification, and publication responsibilities.

## Where to get help

- [Git terms and initial setup](docs/development_workflow.md#a-few-terms-before-you-start).
- [Roles and access permissions](docs/development_workflow.md#how-github-permissions-are-assigned).
- [Contributing through a fork](docs/development_workflow.md#if-you-cannot-push-to-the-shared-repository)
  when you cannot push a branch to the shared repository.
- [Troubleshooting](docs/development_workflow.md#if-a-step-does-not-work).

Ask in the associated issue if the requirements, access, or next step are unclear.
