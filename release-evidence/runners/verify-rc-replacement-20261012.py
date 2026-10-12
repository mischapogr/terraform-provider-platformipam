#!/usr/bin/env python3
"""Apply the saved local Terraform replacement plan after the two e2e cases.

Run only against the isolated development stack with the suite's WORKSPACE
retained. This runner never calls setUpClass, prepares fixtures, rebuilds the
provider, resets the stack or tears down the retained state. It changes one
owned allocation by applying the already inspected saved replacement plan.
"""

import argparse
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys


class CheckFailure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


def identity(record):
    return {name: record.get(name) for name in ("id", "allocation_key", "cidr", "state")}


def run(args):
    root = args.root.resolve(strict=True)
    sys.path.insert(0, str(root / "tests/e2e"))
    import harness
    import test_e2e_terraform as module
    module.TERRAFORM_IMAGE = "hashicorp/terraform:1.14.9@sha256:1d10ec4073f4ddbdf34a28540a3b9250852ab500cb1c53f68c8bd17d82f474d8"
    TerraformE2ETest, WORKSPACE = module.TerraformE2ETest, module.WORKSPACE

    require(harness.ROOT.resolve() == root, "Imported harness does not belong to the requested root")
    case = TerraformE2ETest("test_plan_reserves_nothing_and_apply_is_stable")
    case.stack = harness.stack()
    project = os.environ.get("COMPOSE_PROJECT_NAME") or case.stack.env.get("COMPOSE_PROJECT_NAME")
    require(case.stack.env.get("IPAM_ENVIRONMENT") == "development", "Stack is not development")
    require(project == args.expected_project, "Compose project differs from the isolated qualification project")
    case.api_container = case._api_container()
    case.workspace = WORKSPACE
    config = WORKSPACE / "config-stable"
    require((config / "replacement.tfplan").is_file(), "Kept replacement.tfplan is missing")
    require((config / "terraform.tfstate").is_file(), "Kept stable Terraform state is missing")
    require((WORKSPACE / "plugins/terraform-provider-platformipam").is_file(), "Kept provider binary is missing")
    source_result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                                   capture_output=True, text=True, check=False)
    source_commit = source_result.stdout.strip()
    require(source_result.returncode == 0 and bool(re.fullmatch(r"[0-9a-f]{40}", source_commit)),
            "Frozen checkout has no full source commit identity")
    provider_binary_sha256 = hashlib.sha256(
        (WORKSPACE / "plugins/terraform-provider-platformipam").read_bytes()).hexdigest()
    terraform_version = json.loads(case.terraform("version", "-json", config=config).stdout)
    require(terraform_version.get("terraform_version") == "1.14.9"
            and terraform_version.get("platform") == "linux_amd64", "Terraform runtime differs from the exact qualified CLI target")

    policy_path = root / "providers/terraform/scripts/check-replacement-plan.py"
    spec = importlib.util.spec_from_file_location("qualified_replacement_policy", policy_path)
    policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(policy)

    plan = json.loads(case.terraform("show", "-json", "replacement.tfplan", config=config).stdout)
    require(policy.replacement_errors(plan) == [], "Saved replacement plan fails the consumer guard")
    rows = plan.get("resource_changes", [])
    replacements = [row for row in rows if row.get("mode") == "managed"
                    and row.get("address") == "platformipam_allocation.vpc"]
    require(len(replacements) == 1, "Plan must contain exactly the expected allocation")
    for row in rows:
        if row is not replacements[0]:
            require(row.get("change", {}).get("actions") == ["no-op"],
                    "Plan would change an unexpected resource")
    change = replacements[0]["change"]
    require(set(change["actions"]) == {"create", "delete"}, "Plan is not an allocation replacement")
    before, after = change["before"], change["after"]
    old_id, old_key, old_cidr = (before.get(name) for name in ("id", "allocation_key", "cidr"))
    new_key = after.get("allocation_key")
    require(all(isinstance(value, str) and value for value in (old_id, old_key, old_cidr, new_key)),
            "Saved plan lacks known old identity or new key")
    require(new_key != old_key, "Replacement reuses the old allocation key")

    def get_allocation(allocation_id):
        result = case.stack.api("GET", "/v1/allocations/" + allocation_id)
        require(result.status == 200 and isinstance(result.body, dict), "Allocation cannot be read from the API")
        return result.body

    current = json.loads(case.terraform("show", "-json", config=config).stdout)
    current_rows = current["values"]["root_module"]["resources"]
    current_values = next(row["values"] for row in current_rows
                          if row["address"] == "platformipam_allocation.vpc")
    require(all(current_values.get(name) == before.get(name)
                for name in ("id", "allocation_key", "cidr")), "Current state differs from the saved plan's old identity")
    old_api_before = get_allocation(old_id)
    require(all(old_api_before.get(name) == before.get(name)
                for name in ("id", "allocation_key", "cidr")), "Old API identity differs from the saved plan")
    require(old_api_before.get("state") in ("RESERVED", "ACTIVE"), "Old allocation is not usable before replacement")

    # Apply exactly the same saved plan whose actions and keys passed the guard.
    case.terraform("apply", "-input=false", "replacement.tfplan", config=config)
    resulting_state = json.loads(case.terraform("show", "-json", config=config).stdout)
    resulting_rows = resulting_state["values"]["root_module"]["resources"]
    new_values = next(row["values"] for row in resulting_rows
                      if row["address"] == "platformipam_allocation.vpc")
    new_id, new_cidr = new_values.get("id"), new_values.get("cidr")
    require(isinstance(new_id, str) and new_id and new_id != old_id, "New allocation ID is not distinct")
    require(isinstance(new_cidr, str) and new_cidr and new_cidr != old_cidr, "New allocation CIDR is not distinct")
    require(not ipaddress.ip_network(new_cidr).overlaps(ipaddress.ip_network(old_cidr)),
            "New allocation overlaps the quarantined old CIDR")
    require(new_values.get("allocation_key") == new_key, "New state does not contain the saved plan's new key")

    old_api = get_allocation(old_id)
    require(all(old_api.get(name) == before.get(name) for name in ("id", "allocation_key", "cidr")),
            "Old durable allocation identity was lost")
    require(old_api.get("state") == "QUARANTINED", "Old allocation did not remain durably quarantined")
    require(bool(old_api.get("release_requested_at")) and bool(old_api.get("quarantine_until")),
            "Old allocation lacks persisted release and quarantine timestamps")
    new_api = get_allocation(new_id)
    require(all(new_api.get(name) == new_values.get(name) for name in ("id", "allocation_key", "cidr")),
            "New API identity differs from Terraform state")
    require(new_api.get("state") in ("RESERVED", "ACTIVE"), "New allocation is not usable")
    prefixes = case.stack.netbox_prefixes()
    require(old_cidr in prefixes and new_cidr in prefixes,
            "NetBox does not retain both old quarantine and new allocation prefixes")
    retired_request = {name: before[name] for name in (
        "scope", "environment", "region", "account_id", "address_family", "prefix_length")}
    retired_request["allocation_key"] = old_key
    for name in ("parent_allocation_id", "availability_zone_id"):
        if before.get(name) is not None:
            retired_request[name] = before[name]
    retired_response = case.stack.api("POST", "/v1/allocations", retired_request,
        headers={"Idempotency-Key": "qualification-retired-" + hashlib.sha256(old_id.encode("utf-8")).hexdigest()})
    retired_error = (retired_response.body.get("error", {})
                     if isinstance(retired_response.body, dict) else {})
    require(retired_response.status == 409 and retired_error.get("code") == "allocation_key_retired",
            "Quarantined old key was not refused as effectively retired")
    old_after_refusal = get_allocation(old_id)
    require(all(old_after_refusal.get(name) == old_api.get(name)
                for name in ("id", "allocation_key", "cidr", "state", "release_requested_at", "quarantine_until")),
            "Retired-key refusal changed the old durable allocation")
    require(all(re.fullmatch(r"alloc_[A-Za-z0-9_]{1,120}", value) for value in (old_id, new_id)),
            "Allocation IDs are not safe ledger-query identifiers")
    ids_sql = ", ".join("'" + value + "'" for value in (old_id, new_id))
    # Read only selected identity/lifecycle columns. Never output whole payloads,
    # environment values, credentials, other tenants or unrelated inventory.
    sql = f"""
SELECT json_build_object(
  'allocations', (SELECT coalesce(json_agg(json_build_object(
    'id', id, 'allocation_key', allocation_key, 'committed', committed,
    'payload_id', payload->>'id', 'payload_key', payload->>'allocation_key',
    'cidr', payload->>'cidr', 'state', payload->>'state',
    'release_requested_at', payload->'release_requested_at',
    'quarantine_until', payload->'quarantine_until')), '[]'::json)
    FROM allocations WHERE id IN ({ids_sql})),
  'holds', (SELECT coalesce(json_agg(json_build_object(
    'allocation_id', allocation_id, 'cidr', cidr::text, 'committed', committed)), '[]'::json)
    FROM holds WHERE allocation_id IN ({ids_sql})),
  'keys', (SELECT coalesce(json_agg(json_build_object(
    'allocation_id', allocation_id, 'allocation_key', allocation_key, 'retired', retired)), '[]'::json)
    FROM allocation_keys WHERE allocation_id IN ({ids_sql}))
);
"""
    ledger_result = harness.run(harness.compose_argv(
        "exec", "-T", "platform-db", "psql", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1",
        "-U", case.stack.env.get("PLATFORM_DB_USER", "platform_ipam"),
        "-d", case.stack.env.get("PLATFORM_DB_NAME", "platform_ipam")), stdin=sql)
    require(ledger_result.returncode == 0, "Read-only ledger query failed")
    ledger = json.loads(ledger_result.stdout.strip())
    require(all(len(ledger.get(table, [])) == 2 for table in ("allocations", "holds", "keys")),
            "Ledger must retain exactly the old and new allocation, hold and key rows")
    allocations = {row["id"]: row for row in ledger["allocations"]}
    holds = {row["allocation_id"]: row for row in ledger["holds"]}
    keys = {row["allocation_id"]: row for row in ledger["keys"]}
    require(all(set(rows) == {old_id, new_id} for rows in (allocations, holds, keys)),
            "Ledger contains unexpected or duplicate allocation identities")
    for allocation_id, allocation_key, cidr in ((old_id, old_key, old_cidr), (new_id, new_key, new_cidr)):
        row = allocations[allocation_id]
        require(row["id"] == row["payload_id"] == allocation_id
                and row["allocation_key"] == row["payload_key"] == allocation_key
                and row["cidr"] == cidr and row["committed"] is True,
                "Persisted allocation columns and payload do not retain the expected identity")
        require(holds[allocation_id]["cidr"] == cidr and holds[allocation_id]["committed"] is True,
                "Committed ledger hold is missing or differs from allocation CIDR")
        require(keys[allocation_id]["allocation_key"] == allocation_key,
                "Persisted allocation key differs from the planned identity")
    require(allocations[old_id]["state"] == "QUARANTINED"
            and bool(allocations[old_id]["release_requested_at"])
            and bool(allocations[old_id]["quarantine_until"])
            and keys[old_id]["retired"] is False,
            "Old allocation quarantine, release timestamps or expected pre-terminal key index are not persisted")
    require(allocations[new_id]["state"] in ("RESERVED", "ACTIVE")
            and keys[new_id]["retired"] is False,
            "New allocation is not persisted as usable with an unretired key")
    stable = case.terraform("plan", "-input=false", "-detailed-exitcode", key=new_key,
                            config=config, expect_success=False)
    require(stable.returncode == 0, "Normal plan after replacement is not empty")
    return {
        "status": "PASSED", "check": "replacement_uses_new_key",
        "scope": "isolated_local_api_simulation", "project": project,
        "source_commit": source_commit, "provider_binary_sha256": provider_binary_sha256,
        "provider_address": replacements[0].get("provider_name"),
        "terraform_image": module.TERRAFORM_IMAGE,
        "terraform_version": terraform_version["terraform_version"], "platform": terraform_version["platform"],
        "saved_plan": "replacement.tfplan", "consumer_guard_passed": True,
        "old": identity(old_api), "new": identity(new_api),
        "old_release_requested_at": old_api["release_requested_at"],
        "old_quarantine_until": old_api["quarantine_until"],
        "distinct_id_key_cidr": True, "both_netbox_prefixes_retained": True,
        "ledger": {
            "old_allocation_state": allocations[old_id]["state"],
            "old_release_timestamps_present": True,
            "old_committed_hold_cidr": holds[old_id]["cidr"],
            "old_key_terminal_retired_column": keys[old_id]["retired"],
            "old_key_effectively_retired": True,
            "new_allocation_state": allocations[new_id]["state"],
            "new_committed_hold_cidr": holds[new_id]["cidr"], "new_key_retired": keys[new_id]["retired"],
            "allocation_hold_and_key_identity_match": True,
        },
        "retired_key_reserve_status": retired_response.status,
        "retired_key_reserve_error": retired_error["code"],
        "normal_plan_exit_code": stable.returncode,
        "live_aws": "NOT_READY", "aws_readiness_notice": "AWS API/AWS integration is not yet ready",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Frozen monorepo root used by the kept e2e suite")
    parser.add_argument("--expected-project", default="platform-ipam-preview-e2e-20261010")
    args = parser.parse_args()
    try:
        result = run(args)
    except CheckFailure as error:
        print(json.dumps({"status": "FAILED", "check": "replacement_uses_new_key", "detail": str(error)}))
        return 1
    except Exception as error:
        # Harness exceptions may include captured output. Never echo credentials
        # or Terraform plan/state contents through the qualification summary.
        print(json.dumps({"status": "FAILED", "check": "replacement_uses_new_key", "error_type": type(error).__name__}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
