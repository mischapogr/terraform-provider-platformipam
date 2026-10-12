# Platform-IPAM Terraform provider

This source mirror was exported from `mischapogr/platform-ipam` commit `a88cc5c7f9b718abbb55a9cdef69708acd875326`. The authoritative provider source is `providers/terraform` at that commit. Do not edit this mirror by hand.

Registry publication, main promotion, signer custody and named review remain separate release gates.

Provider versions are independent of Platform-IPAM. See [COMPATIBILITY.md](COMPATIBILITY.md) for the version policy and qualified product pairings; `VERSION` and `COMPATIBILITY.json` must match the release tag.

## Unpromoted preview bootstrap

This is an unpromoted preview source export, not a provider release. It uses committed branch source and does not verify main ancestry.

The approved target repository is `mischapogr/terraform-provider-platformipam`; the selected public provider identity is `registry.terraform.io/mischapogr/platformipam`. Registry publication has not occurred.

Promotion of the reviewed source to monorepo `main`, named maintainer review, Registry enrollment, registered signer custody and release qualification remain required before a signed release.

**AWS API/AWS integration is not yet ready.**


## Build and review

Provider CI uses Go 1.26.9 in a pinned Docker image on standard GitHub-hosted
Ubuntu runners, with module and build caches. It runs formatting, unit tests
a build and version/compatibility metadata checks without API/AWS sandbox access.

The consumer saved-plan guard is `scripts/check-replacement-plan.py`.
Run it on `terraform show -json` output before applying that same saved plan,
including manual replacement and taint.

## Semantic versioning automation

The `Provider release` workflow (`.github/workflows/release.yml`) runs Release
Please on pushes to `main`, or manually from the Actions tab on `main`.
It opens a release PR from Conventional
Commits (`feat:`, `fix:`, `perf:` and `!` / `BREAKING CHANGE:`), updating
`VERSION`, `CHANGELOG.md`, `COMPATIBILITY.json` and its manifest together.
The first PR targets `0.1.0-rc.1`; the manifest records the reviewed candidate
version, while published tags identify actual releases. While the RC configuration is enabled, subsequent
candidates increment the RC number. To move to stable releases, change
`versioning` to `default`, set
`prerelease` to `false`, and remove `prerelease-type` in a reviewed change.
The stable policy uses minor bumps for breaking changes before 1.0.

Automation configuration lives under `.github/`, outside the mirrored source
file set. Release PR changes to mirrored metadata must also be made in the
authoritative monorepo and exported back here before tagging. Update the
human-readable compatibility matrix and qualification evidence for each
candidate; version automation does not establish compatibility or qualification.

Enable **Allow GitHub Actions to create and approve pull requests** in the
repository's Actions settings. The workflow accepts an optional `RELEASE_TOKEN`
secret (a GitHub App token or PAT with contents, issues and pull-request write
access). Use it to trigger CI automatically on bot-created PRs. With the default
`GITHUB_TOKEN`, GitHub suppresses those workflow events; a maintainer must push
a change to the PR branch to trigger its checks before merging.

After a release PR is merged, successful `Provider CI` on the exact `main`
commit triggers publication. The manifest must match `VERSION`, and the
candidate must still be the current `main` commit. The publication job checks
source ancestry, mirror integrity and source-bound qualification, then tests,
builds, packages and signs the provider. Only after those checks pass does it
create the immutable version tag and publish a GitHub Release with the signed
assets and generated changelog notes. RC releases are marked as prereleases.

The initial `0.1.0-rc.1` can also be published by manually running `Provider
release` on `main`, after its CI and release gates pass. If qualification is
completed in a follow-up source export, successful CI on that commit retries
the same recorded version. Tag pushes remain supported for manual releases.
Published versions are skipped; a retry may reuse a tag pointing to the same
commit, but never moves an existing tag or replaces published assets. If tag
creation succeeds but release publication fails, rerun on that exact tag.

The default `GITHUB_TOKEN` can publish in this workflow without triggering
another workflow. Set `RELEASE_TOKEN` if downstream workflows need the tag or
release event. Publication does not require that extra token.

## Signed RC publication

The publication job checks out the immutable monorepo commit in `SOURCE_COMMIT`
and uses its release validators and provider source. Do not edit mirrored source directly or push a version tag
before completing the release gates.

The supplied public RSA-4096 key is stored at
`.github/keys/platformipam-signing-public.asc`, with primary fingerprint
`F1EAE2D8ED6BF46AEEE8889E136F9D1E6B3B2BE8`. Registry registration and private-key custody are
not yet verified. Keep private key material and its passphrase in the secret
store; configure the repository's `GPG_PRIVATE_KEY` and `GPG_PASSPHRASE`
secrets only through the approved custody process.

Before the first release, promote the reviewed source to monorepo `main`,
refresh this mirror using the default (non-preview) exporter, and commit
`RELEASE_QUALIFICATION.json` with named maintainer review and digest-bound
`release-evidence/`. Registry enrollment and an ordinary install of the exact
published package are still required. See the monorepo
[release runbook](https://github.com/mischapogr/platform-ipam/blob/a88cc5c7f9b718abbb55a9cdef69708acd875326/docs/TERRAFORM_PROVIDER_RELEASE.md).

The current bootstrap is not a signed release or Registry publication.
**AWS API/AWS integration is not yet ready.**
