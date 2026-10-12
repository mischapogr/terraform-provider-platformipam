# 0.1.0-rc.1 simulation qualification review

Source: `d1807f4fa6676d6323d7fdddf098b8a39b9fa873`, promoted to
`mischapogr/platform-ipam/main`. The provider is independently versioned and
requires API v1. No Platform-IPAM product release version is claimed supported.

The execution used an isolated local Compose project, real PostgreSQL and
NetBox, fake AWS observations, HTTP fixtures, Go 1.26.9, and Terraform 1.14.9
on linux_amd64. No live AWS testing or production acceptance is claimed.

**AWS API/AWS integration is not yet ready.**

| Required check | Evidence |
| --- | --- |
| Plan does not reserve address space | Two committed Terraform cases; inventory unchanged; CIDR unknown until apply |
| Apply | Committed ID and CIDR agree with API and NetBox; second plan empty |
| Read | Refresh and stable state assertions in the committed Terraform cases |
| Import | Existing ID/CIDR imported; no extra inventory prefix |
| Destroy | API records quarantine rather than immediately freeing space |
| Create timeout recovery | Provider/client fixture test recovers the same ID/key/CIDR without deleting pending reservation |
| Ambiguous read retains identity | Fixture tests retain the full state including known ID/CIDR on 404 and pending 409 |
| Replacement uses a new key | Guarded saved plan applied; distinct ID/key/nonoverlapping CIDR; stable follow-up plan |
| Durable quarantine acceptance | Fixture receipt checks plus persisted old allocation/hold/timestamps and old-key recreation refused with 409 allocation_key_retired |
| Normal installation/checksum refusal | Exact unsigned RC archive installed from filesystem mirror; schema and readonly lock pass; altered package refused |
| Vulnerability scan | Provider and API govulncheck scans completed with zero findings; recorded database timestamp 2026-10-08 |

42 provider tests passed with zero skips. Both Terraform cases passed with
zero skips. All 82 release regressions passed. The provider repository's
13 candidate-selection tests passed. Sanitized logs and assertions are retained
beside this file; [SUMMARY.json](SUMMARY.json) records each evidence digest.

The binary used by both lifecycle and applied-replacement checks has SHA-256
`21ae57f4303686f6b945d9f89f9c3e4d3f2e864df6b52bd086baf38cc6e0d255`.
The exact unsigned archive used by the mirror check has SHA-256
`5dd713570714c027b764b6364acf84300d3720a1d6f3c9fe71d0cfbb132020fa`.

Local mirror installation is not acceptance from the published Registry.
Registry installation must be checked after the signed release is published.

The PostgreSQL allocation_keys.retired column is terminal-state metadata:
it is false while QUARANTINED. Effective permanent key retirement is proved
by the persisted quarantine/release state and the API's refusal to recreate
that key. The evidence makes both facts explicit.

Maintainer `mischapogr` explicitly confirmed review of this evidence on
2026-10-12. The final [release attestation](../RELEASE_QUALIFICATION.json)
records that reviewer and binds all eleven checks to their evidence digests
and the qualified source commit.
