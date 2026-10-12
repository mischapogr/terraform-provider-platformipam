# Platform-IPAM Terraform provider

This source mirror was exported from `mischapogr/platform-ipam` commit `d1807f4fa6676d6323d7fdddf098b8a39b9fa873`. The authoritative provider source is `providers/terraform` at that commit. Do not edit this mirror by hand.

Registry publication, the source namespace, signing key and sandbox acceptance remain separate release gates.

Provider versions are independent of Platform-IPAM. See [COMPATIBILITY.md](COMPATIBILITY.md) for the version policy and qualified product pairings; `VERSION` and `COMPATIBILITY.json` must match the release tag.

## Simulation RC qualification

The exact exported source passed all eleven local simulation checks. See [the evidence review](release-evidence/REVIEW.md) and [digest-bound summary](release-evidence/SUMMARY.json). The [final maintainer attestation](RELEASE_QUALIFICATION.json) records review by `mischapogr` and binds all eleven evidence digests.

The preserved GitHub workflow publishes only after successful Provider CI, source ancestry, mirror/qualification checks and signing. It reads the immutable source from `SOURCE_COMMIT`. Configure `GPG_PRIVATE_KEY` and `GPG_PASSPHRASE` as repository Actions secrets; the matching public signing key must be registered in Terraform Registry.

**AWS API/AWS integration is not yet ready.**

## Build and review

Provider CI uses Go 1.26.9 in a pinned Docker image on standard GitHub-hosted
Ubuntu runners, with module and build caches. It runs formatting, unit tests,
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
candidate must still be the current `main` commit. If the final
`RELEASE_QUALIFICATION.json` is absent, candidate selection records publication
as pending and skips the publish job. The publication job checks source
ancestry, mirror integrity and source-bound qualification, then tests,
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
`F1EAE2D8ED6BF46AEEE8889E136F9D1E6B3B2BE8`. Registry installation verified this registered key on 2026-10-12, and the
maintainer confirmed repository signing-secret setup. Keep private key material
and its passphrase in the secret store; maintain the repository's
`GPG_PRIVATE_KEY` and `GPG_PASSPHRASE` through the approved custody process.

For the next candidate, promote the reviewed source to monorepo `main`,
refresh this mirror using the default (non-preview) exporter, and commit
`RELEASE_QUALIFICATION.json` with named maintainer review and digest-bound
`release-evidence/`. Include its exact-binary
licence/notice packet at `release-evidence/provider-attribution/`; packaging
validates its version, binary digest and complete file hashes before adding
project LICENSE/NOTICE and `THIRD_PARTY_NOTICES/` to the ZIP. Regenerate the
packet for each new binary and retain its dependency review. Registry enrollment
is complete for `0.1.0-rc.1`; verify ordinary installation of each newly published
version. See the monorepo
[release runbook](https://github.com/mischapogr/platform-ipam/blob/835041270e9836ff9690a543bfc847c73633b3c8/docs/TERRAFORM_PROVIDER_RELEASE.md).

Version `0.1.0-rc.1` is signed, simulation-qualified and available in the public
Registry. Fresh published-origin initialization, validation and schema loading
passed with Terraform 1.14.9. Changed packages require a new version and fresh
qualification; preserve existing release assets and consumer checksums.
**AWS API/AWS integration is not yet ready.**
