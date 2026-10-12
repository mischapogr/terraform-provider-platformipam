#!/usr/bin/env python3
"""Select an unpublished, CI-verified candidate without creating remote objects."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPOSITORY = "mischapogr/terraform-provider-platformipam"
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-rc\.(0|[1-9][0-9]*))?")
SHA = re.compile(r"[0-9a-f]{40}")


def api(path):
    request = Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise ValueError(f"GitHub API request failed ({error.code}): {path}") from error


def tag_commit(ref, fetch):
    obj = ref["object"]
    for _ in range(8):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            break
        obj = fetch(f"git/tags/{obj['sha']}")["object"]
    raise ValueError("release tag does not resolve to a commit")


def select(mirror, commit, ref_type, ref_name, fetch=api):
    if not SHA.fullmatch(commit):
        raise ValueError("candidate commit must be a full commit SHA")
    if ref_type != "tag" and (ref_type != "branch" or ref_name != "main"):
        raise ValueError("release candidates must come from main or a version tag")
    version = (mirror / "VERSION").read_text().strip()
    if not SEMVER.fullmatch(version):
        raise ValueError("VERSION must be stable or rc.N SemVer")
    tag = f"v{version}"
    if ref_type == "tag" and ref_name != tag:
        raise ValueError("tag differs from VERSION")
    manifest = json.loads((mirror / ".github/release-please-manifest.json").read_text())
    if manifest.get(".") != version:
        return {"release": False, "reason": "release PR has not recorded this version"}
    if fetch(f"releases/tags/{tag}") is not None:
        return {"release": False, "reason": f"{tag} is already published"}
    main = fetch("git/ref/heads/main")
    if ref_type == "branch" and main["object"]["sha"] != commit:
        return {"release": False, "reason": "candidate was superseded on main"}
    query = urlencode({"head_sha": commit, "event": "push", "branch": "main", "per_page": 100})
    runs = fetch(f"actions/workflows/ci.yml/runs?{query}")
    matches = [run for run in runs["workflow_runs"]
               if run["head_sha"] == commit and run["event"] == "push" and run["head_branch"] == "main"]
    # A newer failed/pending rerun must not be masked by an older successful run.
    latest = max(matches, key=lambda run: (run["run_number"], run.get("run_attempt", 1)), default=None)
    if latest is None or latest["status"] != "completed" or latest["conclusion"] != "success":
        raise ValueError("candidate needs successful Provider CI on its exact main commit")
    source_ref = (mirror / "SOURCE_COMMIT").read_text().strip()
    if not SHA.fullmatch(source_ref):
        raise ValueError("SOURCE_COMMIT must be a full lowercase commit SHA")
    qualification = mirror / "RELEASE_QUALIFICATION.json"
    if not qualification.exists() and not qualification.is_symlink():
        message = "RELEASE_QUALIFICATION.json is pending named maintainer review"
        if ref_type == "tag":
            raise ValueError(f"tagged release requires {message}")
        return {"release": False, "reason": message}
    ref = fetch(f"git/ref/tags/{tag}")
    if ref is not None and tag_commit(ref, fetch) != commit:
        raise ValueError("existing release tag points to a different commit; refusing to move it")
    return {"release": True, "version": version, "tag": tag, "commit": commit,
            "source_ref": source_ref, "tag_exists": ref is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirror", type=Path, default=Path("."))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ref-type", required=True)
    parser.add_argument("--ref-name", required=True)
    args = parser.parse_args()
    try:
        if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
            raise ValueError("publication is restricted to the selected public provider repository")
        result = select(args.mirror, args.commit, args.ref_type, args.ref_name)
        if output := os.environ.get("GITHUB_OUTPUT"):
            with open(output, "a", encoding="utf-8") as stream:
                for key, value in result.items():
                    if isinstance(value, bool):
                        value = str(value).lower()
                    stream.write(f"{key}={value}\n")
        if not result["release"] and (summary := os.environ.get("GITHUB_STEP_SUMMARY")):
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write(f"### Provider publication pending\n\n{result['reason']}\n")
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"release candidate: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
