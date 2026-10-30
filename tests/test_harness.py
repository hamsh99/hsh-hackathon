"""Behavioral regressions using temporary projects, never the user's service."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("harness_installer", KIT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="harness-regression-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "project"
        self.root.mkdir()
        self.assertEqual(installer.install(self.root, True)["status"], "APPLIED")
        self.write("src/logic.py", "def answer():\n    return 3\n")
        self.write("tests/test_logic.py", "import unittest\nfrom src.logic import answer\nclass TestLogic(unittest.TestCase):\n    def test_answer(self): self.assertEqual(answer(), 3)\n")
        self.cfg = json.loads((self.root / "harness/checks.json").read_text())
        self.cfg["originals"] = {"mode": "none", "reason": "합성 테스트 자료만 사용", "paths": []}
        self.cfg["checks"] = [self.unit()]
        self.save()

    def write(self, path, content):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def save(self):
        self.write("harness/checks.json", json.dumps(self.cfg, ensure_ascii=False))

    def unit(self):
        return {"id": "T-001", "feature_ids": ["F-001"], "category": "task", "kind": "unittest",
                "start_dir": "tests", "pattern": "test_*.py", "scope": ["src", "tests"],
                "expected": "answer returns independently specified 3", "timeout_seconds": 5}

    def command(self, code, **extra):
        self.cfg["checks"] = [{"id": "C-001", "feature_ids": ["F-001"], "category": "task", "kind": "command",
                               "purpose": "integration", "command": ["{python}", "-c", code],
                               "scope": ["src"], "expected": "explicit observed output", "stdout_contains": ["ok"], **extra}]
        self.save()

    def cli(self, *args, expected=None):
        result = subprocess.run([sys.executable, str(self.root / "tools/check.py"), "--root", str(self.root), *args],
                                capture_output=True, text=True, timeout=20,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            data = json.loads(result.stdout)
        except ValueError:
            self.fail(f"CLI JSON error: {result.stdout} {result.stderr}")
        if expected is not None:
            self.assertEqual(data["status"], expected, data)
        return data, result.returncode

    def manual(self, scope=None):
        return {"id": "M-UI", "feature_ids": ["F-001"], "category": "task", "kind": "manual",
                "scope": scope or ["src"], "expected": "Human observes real fixture behavior"}

    def pending(self):
        self.cfg["checks"].append(self.manual())
        self.save()
        return self.cli("run", "M-UI", expected="PENDING")[0]

    def confirm(self, pending, **kwargs):
        return self.cli("confirm", pending["run_id"], "--result", "pass", "--observer", "test-reporter",
                        "--observation", "Synthetic regression report; not a real product UI observation", **kwargs)

    def prepare_release(self):
        self.cfg["checks"].append(self.manual(["src", "README.md"]))
        self.cfg["release"] = {"required_checks": ["T-001", "M-UI"], "manual_review_check": "M-UI"}
        self.cfg["submission"] = {"include": ["src", "README.md"], "exclude": [], "required_files": ["src/logic.py", "README.md"]}
        self.save()
        self.cli("run", "T-001", expected="PASS")
        pending = self.cli("run", "M-UI", expected="PENDING")[0]
        self.confirm(pending, expected="PASS")

    def track_originals(self):
        self.write("data/original/input.csv", "id,value\n1,3\n")
        self.cfg["originals"] = {"mode": "tracked", "paths": ["data/original"], "reason": "synthetic original"}
        self.save()
        self.cli("originals", "init", expected="BASELINE_CREATED")

    def test_fresh_project_not_configured(self):
        self.cfg["checks"] = []
        self.save()
        _, code = self.cli("status", expected="NOT_CONFIGURED")
        self.assertNotEqual(code, 0)
        self.cli("release", expected="NOT_READY")

    def test_unittest_pass_records_real_counts_and_snapshot(self):
        result, code = self.cli("run", "T-001", expected="PASS")
        self.assertEqual(code, 0)
        self.assertEqual(result["counts"]["run"], 1)
        saved = json.loads((self.root / result["record_path"]).read_text())
        self.assertIn("src/logic.py", saved["snapshot"]["files"])
        self.assertTrue((self.root / result["log"]).exists())
        self.assertIn(result["run_id"], (self.root / "docs/EVIDENCE.md").read_text())

    def test_zero_tests_not_pass(self):
        self.write("tests/test_logic.py", "# no tests\n")
        _, code = self.cli("run", "T-001", expected="UNVERIFIED")
        self.assertNotEqual(code, 0)

    def test_all_skipped_not_pass(self):
        self.write("tests/test_logic.py", "import unittest\nclass Tests(unittest.TestCase):\n    @unittest.skip('not implemented')\n    def test_missing(self): pass\n")
        result, _ = self.cli("run", "T-001", expected="INCOMPLETE")
        self.assertEqual(result["counts"]["skipped"], 1)

    def test_partial_skip_not_complete(self):
        with (self.root / "tests/test_logic.py").open("a") as out:
            out.write("    @unittest.skip('not implemented')\n    def test_missing(self): pass\n")
        self.cli("run", "T-001", expected="INCOMPLETE")

    def test_wrong_answer_fails(self):
        self.write("src/logic.py", "def answer(): return 8\n")
        self.cli("run", "T-001", expected="FAIL")

    def test_import_error_is_not_zero_success(self):
        self.write("tests/test_logic.py", "import unavailable_example_module_987\n")
        self.cli("run", "T-001", expected="FAIL")

    def test_missing_target_blocked_no_reference_fallback(self):
        (self.root / "src/logic.py").unlink()
        self.cli("run", "T-001", expected="BLOCKED")

    def test_changed_code_invalidates_old_pass(self):
        self.cli("run", "T-001", expected="PASS")
        self.write("src/logic.py", "def answer(): return 4\n")
        result, code = self.cli("status")
        self.assertEqual(result["checks"][0]["status"], "STALE")
        self.assertNotEqual(code, 0)

    def test_new_untracked_source_invalidates(self):
        self.cli("run", "T-001", expected="PASS")
        self.write("src/new_dependency.py", "VALUE = 99\n")
        self.assertEqual(self.cli("status")[0]["checks"][0]["status"], "STALE")

    def test_logs_and_handoff_do_not_invalidate(self):
        self.cli("run", "T-001", expected="PASS")
        self.write("docs/STATE.md", "Only the next action changed\n")
        self.write("artifacts/evidence/note.txt", "summary\n")
        self.assertEqual(self.cli("status")[0]["checks"][0]["status"], "PASS")

    def test_changed_test_definition_invalidates(self):
        self.cli("run", "T-001", expected="PASS")
        self.cfg["checks"][0]["expected"] = "Changed business contract"
        self.save()
        self.assertEqual(self.cli("status")[0]["checks"][0]["status"], "STALE")

    def test_runner_test_directory_automatically_bound(self):
        self.cfg["checks"][0]["scope"] = ["src"]
        self.save()
        self.cli("run", "T-001", expected="PASS")
        with (self.root / "tests/test_logic.py").open("a") as out:
            out.write("# changed test\n")
        self.assertEqual(self.cli("status")[0]["checks"][0]["status"], "STALE")

    def test_latest_failure_not_hidden_by_old_pass(self):
        self.cli("run", "T-001", expected="PASS")
        self.write("src/logic.py", "def answer(): return 7\n")
        self.cli("run", "T-001", expected="FAIL")
        self.assertEqual(self.cli("status")[0]["checks"][0]["status"], "FAIL")

    def test_exit_zero_without_assertion_blocked(self):
        self.command("pass", stdout_contains=[])
        self.cli("run", "C-001", expected="BLOCKED")

    def test_command_expectation_must_be_list(self):
        self.command("print('ok')", stdout_contains="ok")
        self.cli("run", "C-001", expected="BLOCKED")

    def test_command_not_found_records_blocked(self):
        self.command("pass")
        self.cfg["checks"][0]["command"] = ["/missing-harness-command-7b911"]
        self.save()
        result, _ = self.cli("run", "C-001", expected="BLOCKED")
        self.assertIsNone(result["exit_code"])
        self.assertTrue((self.root / result["log"]).exists())

    def test_timeout_is_not_success(self):
        self.command("import time; time.sleep(10)", timeout_seconds=0.1)
        self.cli("run", "C-001", expected="TIMEOUT")

    def test_command_output_assertion_pass(self):
        self.command("print('ok')")
        result, _ = self.cli("run", "C-001", expected="PASS")
        self.assertIsNone(result["counts"])

    def test_old_output_file_does_not_pass(self):
        self.write("output/result.txt", "old")
        self.command("print('ok')", fresh_files=["output/result.txt"])
        self.cli("run", "C-001", expected="INCONCLUSIVE")

    def test_fresh_output_file_passes(self):
        self.command("from pathlib import Path; Path('out.txt').write_text('new'); print('ok')", fresh_files=["out.txt"])
        self.cli("run", "C-001", expected="PASS")

    def test_modifying_source_during_run_records_stale(self):
        self.command("from pathlib import Path; Path('src/logic.py').write_text('changed'); print('ok')")
        self.cli("run", "C-001", expected="STALE")

    def test_deleting_source_during_run_still_records_evidence(self):
        self.command("from pathlib import Path; Path('src/logic.py').unlink(); print('ok')")
        result, _ = self.cli("run", "C-001", expected="STALE")
        self.assertTrue((self.root / "artifacts/evidence" / result["run_id"] / "result.json").exists())

    def test_originals_unchanged_and_starter_edit_allowed(self):
        self.track_originals()
        self.write("src/logic.py", "def answer(): return 99\n")
        self.cli("originals", "verify", expected="PASS")

    def test_original_change_blocks_execution(self):
        self.track_originals()
        self.write("data/original/input.csv", "changed\n")
        result, _ = self.cli("run", "T-001", expected="BLOCKED")
        self.assertIsNone(result["command"])

    def test_original_added_file_detected(self):
        self.track_originals()
        self.write("data/original/extra.csv", "extra")
        self.cli("originals", "verify", expected="FAIL")

    def test_original_changed_during_execution_fails(self):
        self.track_originals()
        self.command("from pathlib import Path; Path('data/original/input.csv').write_text('changed'); print('ok')")
        self.cli("run", "C-001", expected="FAIL")

    def test_original_baseline_never_overwritten(self):
        self.track_originals()
        old = (self.root / "harness/originals.json").read_bytes()
        self.cli("originals", "init", expected="BLOCKED")
        self.assertEqual(old, (self.root / "harness/originals.json").read_bytes())

    def test_manual_is_pending_until_observation(self):
        pending = self.pending()
        result, _ = self.confirm(pending, expected="PASS")
        self.assertEqual(result["observation_source"], "reported-by-caller")
        self.assertIsNone(result["command"])
        original = json.loads((self.root / "artifacts/evidence" / pending["run_id"] / "result.json").read_text())
        self.assertEqual(original["status"], "PENDING")

    def test_manual_change_while_waiting_is_stale(self):
        pending = self.pending()
        self.write("src/logic.py", "def answer(): return 4\n")
        self.confirm(pending, expected="STALE")

    def test_manual_empty_observation_rejected(self):
        pending = self.pending()
        self.cli("confirm", pending["run_id"], "--result", "pass", "--observer", "user", "--observation", "", expected="BLOCKED")

    def test_sandbox_only_own_run_deleted(self):
        self.write("data/user/keep.txt", "user")
        first = self.cli("sandbox", "new")[0]
        second = self.cli("sandbox", "new")[0]
        self.cli("sandbox", "clean", first["id"], expected="REMOVED")
        self.assertEqual((self.root / "data/user/keep.txt").read_text(), "user")
        self.assertTrue(Path(second["path"]).exists())

    def test_sandbox_empty_or_traversal_rejected(self):
        for value in ("", "..", "../data/user", "/tmp", "TMP-invalid"):
            self.cli("sandbox", "clean", value, expected="BLOCKED")

    def test_sandbox_other_project_marker_rejected(self):
        item = self.cli("sandbox", "new")[0]
        self.write(f"work/runs/{item['id']}/.harness-owned.json", '{"project_id":"other","run_id":"wrong"}')
        self.cli("sandbox", "clean", item["id"], expected="BLOCKED")
        self.assertTrue(Path(item["path"]).exists())

    def test_sandbox_symlink_rejected_and_target_preserved(self):
        item = self.cli("sandbox", "new")[0]
        outside = self.root.parent / "outside.txt"
        outside.write_text("keep")
        (Path(item["path"]) / "link").symlink_to(outside)
        self.cli("sandbox", "clean", item["id"], expected="BLOCKED")
        self.assertEqual(outside.read_text(), "keep")

    def test_installer_preview_makes_no_changes(self):
        target = self.root.parent / "preview"
        target.mkdir()
        self.assertEqual(installer.install(target)["status"], "PREVIEW")
        self.assertEqual(list(target.iterdir()), [])

    def test_installer_repeat_preserves_user_docs_and_git_index(self):
        self.write("AGENTS.md", "existing rules\n")
        self.write("docs/STATE.md", "user progress\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(self.root), "add", "AGENTS.md"], check=True)
        index = (self.root / ".git/index").read_bytes()
        result = installer.install(self.root, True)
        self.assertEqual(result["status"], "APPLIED")
        installer.install(self.root, True)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "existing rules\n")
        self.assertEqual((self.root / "docs/STATE.md").read_text(), "user progress\n")
        self.assertEqual((self.root / ".git/index").read_bytes(), index)
        self.assertFalse((self.root / ".gitignore").exists())

    def test_installer_conflict_writes_nothing(self):
        self.write("tools/check.py", "user script")
        (self.root / "harness/START.md").unlink()
        result = installer.install(self.root, True)
        self.assertEqual(result["status"], "CONFLICT")
        self.assertFalse((self.root / "harness/START.md").exists())
        self.assertEqual((self.root / "tools/check.py").read_text(), "user script")

    def test_installer_symlink_destination_rejected(self):
        alternate = self.root.parent / "alias"
        alternate.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(Exception):
            installer.install(alternate, True)

    def test_installer_linked_child_rejected_before_writes(self):
        target = self.root.parent / "linked-child"
        target.mkdir()
        (target / "harness").symlink_to(self.root / "harness", target_is_directory=True)
        with self.assertRaises(Exception):
            installer.install(target, True)
        self.assertFalse((target / "AGENTS.md").exists())

    def test_release_requires_product_checks_and_manual_review(self):
        self.cli("run", "T-001", expected="PASS")
        self.cli("release", expected="NOT_READY")

    def test_release_ready_for_actual_configured_scope(self):
        self.prepare_release()
        result, code = self.cli("release", expected="READY_FOR_SUBMISSION")
        self.assertEqual(code, 0)
        self.assertIn("src/logic.py", result["inventory"])

    def test_release_no_example_as_task_pass(self):
        self.prepare_release()
        self.cfg["checks"][0]["category"] = "example"
        self.save()
        self.cli("run", "T-001", expected="PASS")
        self.cli("release", expected="NOT_READY")

    def test_release_rejects_stale_source(self):
        self.prepare_release()
        self.write("src/logic.py", "def answer(): return 3 # changed\n")
        self.cli("release", expected="NOT_READY")

    def test_release_rejects_unreviewed_submission_file(self):
        self.prepare_release()
        self.write("extra.txt", "new artifact")
        self.cfg["submission"]["include"].append("extra.txt")
        self.save()
        # Re-review with a scope that still omits the new file must not certify it.
        pending = self.cli("run", "M-UI")[0]
        self.confirm(pending, expected="PASS")
        self.cli("release", expected="NOT_READY")

    def test_release_rejects_secret_filename(self):
        self.prepare_release()
        self.write(".env", "FAKE_TEST_ONLY=not-a-key\n")
        self.cfg["submission"]["include"].append(".env")
        self.save()
        result, _ = self.cli("release", expected="NOT_READY")
        self.assertTrue(any("제출 제외" in reason for reason in result["reasons"]))

    def test_release_missing_required_file(self):
        self.prepare_release()
        self.cfg["submission"]["required_files"].append("missing.txt")
        self.save()
        self.cli("release", expected="NOT_READY")

    def test_duplicate_check_ids_blocked(self):
        self.cfg["checks"].append(self.unit())
        self.save()
        self.cli("status", expected="BLOCKED")

    def test_source_symlink_rejected(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("keep")
        (self.root / "src/link.py").symlink_to(outside)
        self.cli("run", "T-001", expected="BLOCKED")

    def test_doctor_read_only_and_not_product_pass(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = subprocess.run([sys.executable, str(self.root / "tools/doctor.py"), "--root", str(self.root)], capture_output=True, text=True)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "ENVIRONMENT_ONLY")
        self.assertEqual(data["auto_skill_detection"], "NOT_VERIFIED")
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
