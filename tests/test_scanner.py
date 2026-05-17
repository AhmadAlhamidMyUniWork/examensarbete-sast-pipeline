import io
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import scanner


def make_zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries:
            if isinstance(content, zipfile.ZipInfo):
                zf.writestr(content, "")
            else:
                zf.writestr(name, content)
    return buf.getvalue()


def make_symlink_info(name, target):
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = 0o120777 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    info.file_size = len(target)
    return info


class SafeExtractZipTests(unittest.TestCase):
    def test_extracts_normal_files(self):
        zip_bytes = make_zip([
            ("src/main.py", "print('ok')\n"),
            ("README.md", "hello\n"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            meta = scanner.safe_extract_zip(zip_bytes=zip_bytes, dest_dir=tmp)
            self.assertEqual(meta["extracted_files"], 2)
            self.assertEqual(meta["skipped_files"], 0)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "src/main.py")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "README.md")))

    def test_blocks_zip_slip_paths(self):
        zip_bytes = make_zip([
            ("../evil.txt", "bad"),
            ("safe.txt", "ok"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            meta = scanner.safe_extract_zip(zip_bytes=zip_bytes, dest_dir=tmp)
            self.assertEqual(meta["extracted_files"], 1)
            self.assertEqual(meta["skipped_files"], 1)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "safe.txt")))
            self.assertFalse(os.path.exists(os.path.join(os.path.dirname(tmp), "evil.txt")))

    def test_skips_symlink_entries(self):
        link_info = make_symlink_info("bad_link", "target.txt")
        zip_bytes = make_zip([
            ("safe.txt", "ok"),
            ("bad_link", link_info),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            meta = scanner.safe_extract_zip(zip_bytes=zip_bytes, dest_dir=tmp)
            self.assertEqual(meta["extracted_files"], 1)
            self.assertEqual(meta["skipped_files"], 1)
            self.assertFalse(os.path.lexists(os.path.join(tmp, "bad_link")))

    def test_enforces_max_files(self):
        zip_bytes = make_zip([
            ("a.txt", "a"),
            ("b.txt", "b"),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                scanner.safe_extract_zip(zip_bytes=zip_bytes, dest_dir=tmp, max_files=1)

    def test_enforces_max_total_bytes(self):
        zip_bytes = make_zip([
            ("big.txt", "x" * 200),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                scanner.safe_extract_zip(zip_bytes=zip_bytes, dest_dir=tmp, max_total_bytes=100)


class AggregationTests(unittest.TestCase):
    def test_dedupe_and_summary_and_policy(self):
        finding = {
            "fingerprint": "dup",
            "severity": "high",
            "category": "other",
            "tool": "bandit",
            "file": "a.py",
            "start_line": 1,
            "message": "x",
            "recommendation": "y",
        }
        deduped = scanner.dedupe([finding, dict(finding)])
        self.assertEqual(len(deduped), 1)
        summary = scanner.summarize(deduped)
        self.assertEqual(summary["severity_counts"]["high"], 1)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(scanner.policy_decision(summary), "WARN")


class FullScanTests(unittest.TestCase):
    def test_run_full_scan_happy_path_with_mocked_tools(self):
        zip_bytes = make_zip([("app.py", "print('hello')\n")])
        base_finding = {
            "fingerprint": "f1",
            "category": "other",
            "severity": "medium",
            "confidence": "medium",
            "tool": "bandit",
            "rule_id": "B000",
            "file": "app.py",
            "start_line": 1,
            "end_line": 1,
            "message": "test finding",
            "recommendation": "fix",
        }
        with patch.object(scanner, "run_bandit", return_value=([base_finding], "bandit log")), \
             patch.object(scanner, "run_semgrep", return_value=([], "semgrep log")), \
             patch.object(scanner, "run_detect_secrets", return_value=([], "secrets log")), \
             patch.object(scanner, "run_pip_audit", return_value=([], "audit log")):
            report = scanner.run_full_scan(zip_bytes=zip_bytes, job_id="job-1")

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["job_id"], "job-1")
        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["decision"], "WARN")
        self.assertIn("bandit", report["tool_logs"])
        self.assertIn("semgrep", report["tool_logs"])
        self.assertIn("detect-secrets", report["tool_logs"])
        self.assertIn("pip-audit", report["tool_logs"])

    def test_run_full_scan_returns_error_on_extraction_failure(self):
        zip_bytes = make_zip([("a.py", "print(1)\n")])
        report = scanner.run_full_scan(zip_bytes=zip_bytes, job_id="job-2", max_files=0)
        self.assertEqual(report["status"], "error")
        self.assertEqual(report["decision"], "FAIL")
        self.assertEqual(report["summary"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
