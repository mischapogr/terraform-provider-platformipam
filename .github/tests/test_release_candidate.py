import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "release_candidate", Path(__file__).parents[1] / "scripts/release-candidate.py")
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
COMMIT = "a" * 40
SOURCE = "b" * 40


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.mirror = Path(self.directory.name)
        (self.mirror / ".github").mkdir()
        (self.mirror / "VERSION").write_text("0.1.0-rc.1\n")
        (self.mirror / "SOURCE_COMMIT").write_text(SOURCE + "\n")
        (self.mirror / ".github/release-please-manifest.json").write_text('{".": "0.1.0-rc.1"}')
        self.published = None
        self.tag = None
        self.main = COMMIT
        self.runs = [self.ci_run(1, "completed", "success")]
        self.requests = []

    @staticmethod
    def ci_run(number, status, conclusion, **extra):
        return {"run_number": number, "head_sha": COMMIT, "event": "push", "head_branch": "main",
                "status": status, "conclusion": conclusion, **extra}

    def fetch(self, path):
        self.requests.append(path)
        if path.startswith("releases/tags/"):
            return self.published
        if path == "git/ref/heads/main":
            return {"object": {"sha": self.main, "type": "commit"}}
        if path.startswith("actions/workflows/ci.yml/runs?"):
            return {"workflow_runs": self.runs}
        if path.startswith("git/ref/tags/"):
            return self.tag
        if path.startswith("git/tags/"):
            return {"object": {"type": "commit", "sha": COMMIT}}
        self.fail(f"unexpected API request: {path}")

    def select(self, ref_type="branch", ref_name="main"):
        return candidate.select(self.mirror, COMMIT, ref_type, ref_name, self.fetch)

    def test_merged_rc_selects_exact_version_and_source(self):
        result = self.select()
        self.assertEqual(result, {"release": True, "version": "0.1.0-rc.1", "tag": "v0.1.0-rc.1",
                                  "commit": COMMIT, "source_ref": SOURCE, "tag_exists": False})

    def test_unmerged_version_creates_nothing(self):
        (self.mirror / ".github/release-please-manifest.json").write_text("{}")
        self.assertFalse(self.select()["release"])
        self.assertEqual(self.requests, [])

    def test_published_version_is_skipped(self):
        self.published = {"tag_name": "v0.1.0-rc.1"}
        self.assertFalse(self.select()["release"])

    def test_stale_main_commit_is_skipped(self):
        self.main = "c" * 40
        self.assertFalse(self.select()["release"])

    def test_ci_must_pass_on_exact_main_push(self):
        cases = [[], [self.ci_run(1, "completed", "failure")], [self.ci_run(1, "in_progress", None)],
                 [self.ci_run(1, "completed", "success", head_sha="c" * 40)],
                 [self.ci_run(1, "completed", "success", event="pull_request")]]
        for runs in cases:
            with self.subTest(runs=runs):
                self.runs = runs
                with self.assertRaisesRegex(ValueError, "successful Provider CI"):
                    self.select()

    def test_newer_failed_run_does_not_reuse_previous_success(self):
        self.runs.append(self.ci_run(2, "completed", "failure"))
        with self.assertRaisesRegex(ValueError, "successful Provider CI"):
            self.select()

    def test_retry_can_reuse_same_commit_tag(self):
        self.tag = {"object": {"type": "commit", "sha": COMMIT}}
        self.assertTrue(self.select()["tag_exists"])

    def test_annotated_tag_is_peeled(self):
        self.tag = {"object": {"type": "tag", "sha": "c" * 40}}
        self.assertTrue(self.select("tag", "v0.1.0-rc.1")["tag_exists"])

    def test_tag_cannot_be_moved(self):
        self.tag = {"object": {"type": "commit", "sha": "c" * 40}}
        with self.assertRaisesRegex(ValueError, "refusing to move"):
            self.select()

    def test_tag_must_match_candidate_version(self):
        with self.assertRaisesRegex(ValueError, "differs from VERSION"):
            self.select("tag", "v0.2.0")

    def test_non_main_branch_is_refused(self):
        with self.assertRaisesRegex(ValueError, "main or a version tag"):
            self.select("branch", "release-please--branches--main")

    def test_stable_candidate_is_supported(self):
        (self.mirror / "VERSION").write_text("0.1.0\n")
        (self.mirror / ".github/release-please-manifest.json").write_text('{".": "0.1.0"}')
        self.assertEqual(self.select()["tag"], "v0.1.0")

    def test_invalid_source_and_version_are_refused(self):
        (self.mirror / "SOURCE_COMMIT").write_text("main\n")
        with self.assertRaisesRegex(ValueError, "SOURCE_COMMIT"):
            self.select()
        for version in ("0.1.0-rc.01", "0.1.0+build", "v0.1.0", "0.1.0-beta.1"):
            with self.subTest(version=version):
                (self.mirror / "VERSION").write_text(version)
                with self.assertRaisesRegex(ValueError, "SemVer"):
                    self.select()


if __name__ == "__main__":
    unittest.main()
