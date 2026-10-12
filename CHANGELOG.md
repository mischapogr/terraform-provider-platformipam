# Provider changelog

This provider is independently versioned using [Semantic Versioning](https://semver.org/).
Published entries must include their source commit, compatibility matrix and
migration notes when required. No provider version has been published yet.

## 0.1.0-rc.1 (2026-10-12)


### Features

* add independent SemVer and Platform-IPAM compatibility matrix ([3104369](https://github.com/mischapogr/terraform-provider-platformipam/commit/310436945f40966298c321e0131c73446c95c3a2))
* bootstrap platformipam provider source mirror ([4ac9817](https://github.com/mischapogr/terraform-provider-platformipam/commit/4ac9817700b4b50264cf92671ff8f94a0769bc6e))
* **ci:** automate provider release candidate versioning ([2d25357](https://github.com/mischapogr/terraform-provider-platformipam/commit/2d253571c5df4fe6ae3372987104c06afafa04b1))


### Bug Fixes

* **ci:** update action runtimes and pin Ubuntu runner ([6f72247](https://github.com/mischapogr/terraform-provider-platformipam/commit/6f72247917d4f32ebfdb6056b194a1e6e00e0778))

## 0.1.0-rc.1 — planned, unpublished

- Allocation resource; read-only allocation and pool data sources; import,
  durable allocation identity and quarantine-aware deletion.
- Explicit replacement plan guard and diagnostics for ambiguous reads.
- Independent provider version metadata and an API/product compatibility matrix.
- API v1 required. No Platform-IPAM product release is qualified yet.
- Simulation only. **AWS API/AWS integration is not yet ready.**
