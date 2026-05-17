import hashlib
import io
import json
import os
import re
import stat
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------
# Safety limits (default)
# ----------------------------
DEFAULT_MAX_TOTAL_BYTES = 500 * 1024 * 1024   # 500MB extracted
DEFAULT_MAX_FILES = 50_000
DEFAULT_TIMEOUT_SEC = 120

LOCAL_SEMGREP_RULES = """rules:
  - id: local.python.eval-use
    patterns:
      - pattern: eval(...)
    message: Avoid eval on untrusted input.
    severity: ERROR
    languages: [python]
  - id: local.python.subprocess-shell-true
    patterns:
      - pattern: subprocess.$F(..., shell=True, ...)
    message: Avoid shell=True with untrusted input.
    severity: WARNING
    languages: [python]
  - id: local.python.weak-hash-md5
    patterns:
      - pattern: hashlib.md5(...)
    message: MD5 is weak for security-sensitive hashing.
    severity: INFO
    languages: [python]
"""


TOOL_EXECUTABLES = ["bandit", "semgrep", "detect-secrets", "pip-audit"]


def _resolve_executable(executable: str) -> str:
    # Prefer PATH, then fall back to project-local virtualenv binaries.
    if os.path.isabs(executable):
        return executable
    path_hit = shutil.which(executable)
    if path_hit:
        return path_hit
    local_venv_bin = os.path.join(os.path.dirname(__file__), ".venv", "bin", executable)
    if os.path.isfile(local_venv_bin) and os.access(local_venv_bin, os.X_OK):
        return local_venv_bin
    return executable


def get_tool_runtime_status() -> Dict[str, Dict[str, Any]]:
    status: Dict[str, Dict[str, Any]] = {}
    for tool in TOOL_EXECUTABLES:
        resolved = _resolve_executable(tool)
        is_available = (
            os.path.isabs(resolved)
            and os.path.isfile(resolved)
            and os.access(resolved, os.X_OK)
        )
        status[tool] = {
            "available": is_available,
            "resolved_path": resolved,
        }
    return status

# ----------------------------
# Finding schema
# ----------------------------
def fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8", errors="ignore"))
        h.update(b"\0")
    return h.hexdigest()

def norm_severity(s: str) -> str:
    s = (s or "").strip().lower()
    mapping = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "low",
        "warning": "medium",
        "error": "high",
    }
    return mapping.get(s, "medium")

def guess_category(message: str, rule: str = "") -> str:
    text = f"{rule} {message}".lower()
    if "sql" in text or "injection" in text:
        return "injection"
    if "ssrf" in text or "request" in text and "url" in text:
        return "ssrf"
    if "secret" in text or "apikey" in text or "token" in text or "password" in text:
        return "secrets"
    if "crypto" in text or "md5" in text or "sha1" in text or "weak" in text:
        return "crypto"
    if "auth" in text or "jwt" in text or "csrf" in text or "cors" in text:
        return "auth"
    if "dependency" in text or "cve" in text or "vulnerab" in text:
        return "deps"
    return "other"

# ----------------------------
# Safe ZIP extraction
# ----------------------------
def _is_bad_path(base: str, target: str) -> bool:
    base = os.path.abspath(base)
    target = os.path.abspath(target)
    return not target.startswith(base + os.sep)

def safe_extract_zip(
    zip_bytes: bytes,
    dest_dir: str,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
) -> Dict[str, Any]:
    """
    Extracts zip to dest_dir while protecting against zip-slip and zip bombs.
    Returns metadata about extraction.
    """
    total = 0
    count = 0
    skipped = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for info in z.infolist():
            # Skip directories
            if info.is_dir():
                continue

            count += 1
            if count > max_files:
                raise ValueError(f"Too many files in archive (>{max_files}).")

            # Prevent zip-slip
            out_path = os.path.join(dest_dir, info.filename)
            if _is_bad_path(dest_dir, out_path):
                skipped += 1
                continue

            # Reject absolute paths and weird names
            if os.path.isabs(info.filename) or info.filename.startswith(("\\", "/")):
                skipped += 1
                continue

            # Ignore symlink entries
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                skipped += 1
                continue

            # Basic zip bomb guard (sum of uncompressed sizes)
            total += int(info.file_size or 0)
            if total > max_total_bytes:
                raise ValueError(f"Archive too large after extraction (>{max_total_bytes} bytes).")

            # Create parent dirs
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            # Extract file safely (no symlink handling in zipfile; but still avoid writing special)
            with z.open(info) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

    return {"extracted_files": count - skipped, "skipped_files": skipped, "total_bytes": total}

# ----------------------------
# Subprocess helper
# ----------------------------
def run_cmd(cmd: List[str], cwd: str, timeout: int = DEFAULT_TIMEOUT_SEC) -> Tuple[int, str]:
    resolved_cmd = list(cmd)
    if resolved_cmd:
        resolved_cmd[0] = _resolve_executable(resolved_cmd[0])
    try:
        p = subprocess.run(
            resolved_cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )
        return p.returncode, p.stdout
    except FileNotFoundError:
        local_hint = os.path.join(os.path.dirname(__file__), ".venv", "bin", cmd[0])
        return 127, (
            f"ERROR: Tool '{cmd[0]}' not found. "
            f"Tried PATH and '{local_hint}'. "
            "Install requirements and run Streamlit from the project environment."
        )
    except subprocess.TimeoutExpired as e:
        return 124, f"TIMEOUT: {e}"
    except Exception as e:
        return 1, f"ERROR: {e}"

def find_requirements_file(root: str) -> Optional[str]:
    candidates = ["requirements.txt", "requirements-dev.txt", "requirements/prod.txt"]
    for c in candidates:
        p = os.path.join(root, c)
        if os.path.isfile(p):
            return p
    return None

# ----------------------------
# Tool runners
# ----------------------------
def run_bandit(project_dir: str) -> Tuple[List[Dict[str, Any]], str]:
    out_json = os.path.join(project_dir, ".bandit.json")
    cmd = ["bandit", "-r", ".", "-f", "json", "-o", out_json]
    rc, log = run_cmd(cmd, cwd=project_dir)
    findings: List[Dict[str, Any]] = []
    if os.path.exists(out_json):
        try:
            data = json.load(open(out_json, "r", encoding="utf-8"))
            for item in data.get("results", []):
                sev = norm_severity(item.get("issue_severity", "medium"))
                conf = (item.get("issue_confidence") or "medium").lower()
                file_path = item.get("filename", "")
                line = int(item.get("line_number") or 0)
                test_id = item.get("test_id", "")
                msg = item.get("issue_text", "Bandit finding")
                rec = item.get("more_info", "")
                findings.append({
                    "fingerprint": fingerprint("bandit", test_id, file_path, str(line), msg),
                    "category": guess_category(msg, test_id),
                    "severity": sev,
                    "confidence": conf,
                    "tool": "bandit",
                    "rule_id": test_id,
                    "file": file_path,
                    "start_line": line,
                    "end_line": line,
                    "message": msg,
                    "recommendation": rec or "Review the flagged code path and apply secure alternatives.",
                })
        except Exception:
            pass
    return findings, log

def run_semgrep(project_dir: str) -> Tuple[List[Dict[str, Any]], str]:
    out_json = os.path.join(project_dir, ".semgrep.json")
    # Using recommended rulesets: python + security-audit (can tune later)
    cmd = ["semgrep", "scan", "--config", "p/python", "--config", "p/security-audit", "--json", "-o", out_json, "."]
    rc, log = run_cmd(cmd, cwd=project_dir)
    if rc != 0 or not os.path.exists(out_json):
        fallback_rules = os.path.join(project_dir, ".semgrep-local.yml")
        try:
            with open(fallback_rules, "w", encoding="utf-8") as f:
                f.write(LOCAL_SEMGREP_RULES)
            fallback_cmd = ["semgrep", "scan", "--config", fallback_rules, "--json", "-o", out_json, "."]
            frc, flog = run_cmd(fallback_cmd, cwd=project_dir)
            log = f"{log}\n\n[FALLBACK local rules rc={frc}]\n{flog}".strip()
        except Exception as e:
            log = f"{log}\n\n[FALLBACK local rules error] {e}".strip()
    findings: List[Dict[str, Any]] = []
    if os.path.exists(out_json):
        try:
            data = json.load(open(out_json, "r", encoding="utf-8"))
            for r in data.get("results", []):
                check_id = r.get("check_id", "semgrep.rule")
                extra = r.get("extra", {}) or {}
                msg = (extra.get("message") or "Semgrep finding").strip()
                sev = norm_severity((extra.get("severity") or "medium"))
                conf = "medium"
                path = r.get("path", "")
                start = (r.get("start", {}) or {}).get("line", 0) or 0
                end = (r.get("end", {}) or {}).get("line", start) or start
                rec = (extra.get("fix") or "") or "Apply secure coding guidance for this rule."
                findings.append({
                    "fingerprint": fingerprint("semgrep", check_id, path, str(start), msg),
                    "category": guess_category(msg, check_id),
                    "severity": sev,
                    "confidence": conf,
                    "tool": "semgrep",
                    "rule_id": check_id,
                    "file": path,
                    "start_line": int(start),
                    "end_line": int(end),
                    "message": msg,
                    "recommendation": rec,
                })
        except Exception:
            pass
    return findings, log

def run_detect_secrets(project_dir: str) -> Tuple[List[Dict[str, Any]], str]:
    # detect-secrets outputs a "snapshot" JSON
    cmd = ["detect-secrets", "scan", "--all-files", "--no-verify", "."]
    rc, log = run_cmd(cmd, cwd=project_dir)
    findings: List[Dict[str, Any]] = []
    # detect-secrets prints JSON to stdout typically
    try:
        data = json.loads(log)
        results = data.get("results", {}) or {}
        for file_path, items in results.items():
            for it in items:
                line = int(it.get("line_number") or 0)
                typ = it.get("type", "Secret")
                hashed = it.get("hashed_secret", "")
                msg = f"Potential secret: {typ}"
                findings.append({
                    "fingerprint": fingerprint("detect-secrets", typ, file_path, str(line), hashed),
                    "category": "secrets",
                    "severity": "high",
                    "confidence": "medium",
                    "tool": "detect-secrets",
                    "rule_id": typ,
                    "file": file_path,
                    "start_line": line,
                    "end_line": line,
                    "message": msg,
                    "recommendation": "Remove the secret from code. Rotate credentials. Store secrets in a vault / env vars.",
                })
    except Exception:
        # If parsing fails, just return empty findings with logs shown in UI
        pass
    return findings, log

def run_pip_audit(project_dir: str) -> Tuple[List[Dict[str, Any]], str]:
    req = find_requirements_file(project_dir)
    findings: List[Dict[str, Any]] = []
    if req:
        cmd = ["pip-audit", "-r", req, "-f", "json"]
    else:
        # Try pyproject-based audit (works for many projects)
        cmd = ["pip-audit", "-f", "json"]
    rc, log = run_cmd(cmd, cwd=project_dir)
    try:
        json_start = log.find("{")
        if json_start == -1:
            json_start = log.find("[")
        pip_data = json.loads(log[json_start:]) if json_start != -1 else []
        data = pip_data.get("dependencies", pip_data) if isinstance(pip_data, dict) else pip_data
        
        # pip-audit JSON is a list of dependencies with vulns
        for dep in data:
            name = dep.get("name", "package")
            version = dep.get("version", "")
            vulns = dep.get("vulns", []) or []
            for v in vulns:
                vuln_id = v.get("id", "VULN")
                desc = (v.get("description") or "").strip()
                fix_versions = v.get("fix_versions", []) or []
                msg = f"{name} {version} vulnerable: {vuln_id}"
                rec = f"Upgrade {name}. Suggested fix versions: {', '.join(fix_versions) or 'see advisory'}"
                findings.append({
                    "fingerprint": fingerprint("pip-audit", name, version, vuln_id),
                    "category": "deps",
                    "severity": "high",
                    "confidence": "high",
                    "tool": "pip-audit",
                    "rule_id": vuln_id,
                    "file": req or "pyproject.toml",
                    "start_line": abs(hash(f"{name}:{vuln_id}")) % 999999 + 1,
                    "end_line": abs(hash(f"{name}:{vuln_id}")) % 999999 + 1,
                    "message": msg if not desc else f"{msg} - {desc[:200]}",
                    "recommendation": rec,
                })
    except Exception:
        pass
    return findings, log

# ----------------------------
# Aggregation & policy
# ----------------------------
# NY kod – ersätt med denna:
SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

def dedupe(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {}
    
    for f in findings:
        overlap_fp = fingerprint(
            os.path.basename(f["file"]),
            str(f["start_line"]),
            f["category"]
        )
        
        if overlap_fp in seen:
            existing = seen[overlap_fp]
            existing["tools"].append(f["tool"])
            if SEVERITY_RANK[existing["severity"]] < SEVERITY_RANK[f["severity"]]:
                existing["severity"] = f["severity"]
        else:
            new_finding = dict(f)
            new_finding["tools"] = [f["tool"]]
            seen[overlap_fp] = new_finding
    
    return list(seen.values())

def summarize(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        s = f.get("severity", "medium")
        counts[s] = counts.get(s, 0) + 1
    return {"severity_counts": counts, "total": len(findings)}

def policy_decision(summary: Dict[str, Any]) -> str:
    c = summary.get("severity_counts", {})
    if c.get("critical", 0) > 0:
        return "FAIL"
    if c.get("high", 0) >= 5:
        return "FAIL"
    if c.get("high", 0) > 0 or c.get("medium", 0) > 0:
        return "WARN"
    return "PASS"

# ----------------------------
# Main entry point
# ----------------------------
def run_full_scan(
    zip_bytes: bytes,
    job_id: str,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
) -> Dict[str, Any]:
    tool_logs: Dict[str, str] = {}
    all_findings: List[Dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix=f"scan_{job_id}_") as tmp:
        project_dir = os.path.join(tmp, "project")
        os.makedirs(project_dir, exist_ok=True)

        try:
            extract_meta = safe_extract_zip(
                zip_bytes=zip_bytes,
                dest_dir=project_dir,
                max_total_bytes=max_total_bytes,
                max_files=max_files,
            )
        except Exception as e:
            return {
                "status": "error",
                "job_id": job_id,
                "error": f"Extraction failed: {e}",
                "findings": [],
                "summary": summarize([]),
                "decision": "FAIL",
                "tool_logs": {},
            }

        # Run tools (best-effort)
        bandit_findings, bandit_log = run_bandit(project_dir)
        tool_logs["bandit"] = bandit_log
        all_findings.extend(bandit_findings)

        semgrep_findings, semgrep_log = run_semgrep(project_dir)
        tool_logs["semgrep"] = semgrep_log
        all_findings.extend(semgrep_findings)

        secrets_findings, secrets_log = run_detect_secrets(project_dir)
        tool_logs["detect-secrets"] = secrets_log
        all_findings.extend(secrets_findings)

        audit_findings, audit_log = run_pip_audit(project_dir)
        tool_logs["pip-audit"] = audit_log
        all_findings.extend(audit_findings)

        all_findings = dedupe(all_findings)
        summary = summarize(all_findings)
        decision = policy_decision(summary)

        return {
            "status": "ok",
            "job_id": job_id,
            "extraction": extract_meta,
            "summary": summary,
            "decision": decision,
            "findings": all_findings,
            "tool_logs": tool_logs,
        }
