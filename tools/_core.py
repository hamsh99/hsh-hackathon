"""Small local harness. Standard library only; no networking or shell=True."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

VERSION = "1.0.0"
CONFIG = "harness/checks.json"
MARKER = "harness/project.json"
ORIGINALS = "harness/originals.json"
IGNORED_PARTS = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache"}
RECORDS = {"docs/TASK.md", "docs/STATE.md", "docs/DECISIONS.md", "docs/EVIDENCE.md"}
CATEGORIES = {"task", "harness", "example", "environment"}


class HarnessError(Exception):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def identifier(prefix="RUN"):
    return prefix + "-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HarnessError(f"JSON을 읽을 수 없음: {path.name}: {exc}") from exc


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2)
        out.write("\n")


def safe_path(root, relative, *, must_exist=False, allow_root=False):
    if not isinstance(relative, str) or not relative.strip():
        raise HarnessError("빈 경로는 허용하지 않음")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise HarnessError(f"프로젝트 밖 경로 거부: {relative}")
    if not allow_root and str(rel) == ".":
        raise HarnessError("프로젝트 전체 대신 필요한 파일·폴더를 지정하세요")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise HarnessError(f"심볼릭 링크 경로 거부: {relative}")
    target = root / rel
    if not target.resolve().is_relative_to(root):
        raise HarnessError(f"프로젝트 밖 경로 거부: {relative}")
    if must_exist and not target.exists():
        raise HarnessError(f"대상 없음: {relative}")
    return target


def collect(root, paths, *, exclude_records=False, ignore_generated=True):
    if not isinstance(paths, list) or not paths:
        raise HarnessError("대상 경로를 하나 이상 지정하세요")
    found = {}
    for rel in paths:
        base = safe_path(root, rel, must_exist=True)
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        count = 0
        for path in candidates:
            name = path.relative_to(root).as_posix()
            # Reject links before filtering: never follow a link in a selected tree.
            safe_path(root, name)
            if ignore_generated and any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
                continue
            if exclude_records and (name in RECORDS or name.startswith(("artifacts/", "work/"))):
                continue
            if path.is_file():
                found[name] = file_hash(path)
                count += 1
        if not count:
            raise HarnessError(f"검증할 파일이 없는 대상: {rel}")
    return dict(sorted(found.items()))


def context(root):
    root = Path(root).resolve()
    marker = load(safe_path(root, MARKER, must_exist=True))
    cfg = load(safe_path(root, CONFIG, must_exist=True))
    if not isinstance(marker, dict) or not marker.get("project_id"):
        raise HarnessError("설치 식별자가 없음. install.py로 적용하세요")
    if cfg.get("version") != 1 or not isinstance(cfg.get("checks"), list):
        raise HarnessError("checks.json 형식 오류")
    ids = [c.get("id") for c in cfg["checks"]]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids):
        raise HarnessError("검사 ID가 없거나 중복·잘못된 형식")
    return root, marker, cfg


def find_check(cfg, check_id):
    for check in cfg["checks"]:
        if check["id"] == check_id:
            return check
    raise HarnessError(f"등록되지 않은 검사: {check_id}")


def validate_check(root, check):
    if check.get("category") not in CATEGORIES:
        raise HarnessError("category는 task/harness/example/environment 중 하나여야 함")
    if check.get("kind") not in {"unittest", "command", "manual"}:
        raise HarnessError("지원 검사: unittest, command, manual")
    if not isinstance(check.get("feature_ids"), list) or not check.get("expected", "").strip():
        raise HarnessError("feature_ids와 expected를 명시하세요")
    timeout = check.get("timeout_seconds", 60)
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
        raise HarnessError("timeout_seconds는 0 초과 600 이하")
    cwd = safe_path(root, check.get("cwd", "."), must_exist=True, allow_root=True)
    if not cwd.is_dir():
        raise HarnessError("cwd는 디렉토리여야 함")
    if check["kind"] == "unittest":
        start = safe_path(root, check.get("start_dir", "tests"), must_exist=True)
        if not start.is_dir() or Path(check.get("pattern", "test_*.py")).name != check.get("pattern", "test_*.py"):
            raise HarnessError("잘못된 unittest 디렉토리 또는 pattern")
    if check["kind"] == "command":
        command = check.get("command")
        if not isinstance(command, list) or not command or any(not isinstance(a, str) or not a for a in command):
            raise HarnessError("command는 비어 있지 않은 문자열 배열이어야 함")
        if check.get("purpose") not in {"build", "lint", "integration", "environment"}:
            raise HarnessError("일반 명령 purpose를 지정하세요. 테스트 개수 검사는 unittest를 사용하세요")
        if not check.get("stdout_contains") and not check.get("fresh_files"):
            raise HarnessError("종료 코드만으로 통과할 수 없음. stdout_contains 또는 fresh_files 필요")
        for key in ("stdout_contains", "fresh_files"):
            values = check.get(key, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                raise HarnessError(f"{key}는 비어 있지 않은 문자열의 배열이어야 함")
        for path in check.get("fresh_files", []):
            safe_path(root, path)


def snapshot(root, marker, check):
    validate_check(root, check)
    paths = check.get("scope")
    if not isinstance(paths, list) or not paths:
        raise HarnessError("제품 검증 대상 scope가 비어 있음")
    paths = list(paths)
    if check["kind"] == "unittest" and check.get("start_dir", "tests") not in paths:
        paths.append(check.get("start_dir", "tests"))
    files = collect(root, paths, exclude_records=True)
    engine = {}
    for name in ("_core.py", "_unittest_runner.py", "check.py"):
        path = Path(__file__).parent / name
        engine[name] = file_hash(path)
    original = safe_path(root, ORIGINALS)
    cfg = load(safe_path(root, CONFIG, must_exist=True))
    payload = {"project_id": marker["project_id"], "definition": check, "files": files,
               "engine": engine, "python": sys.version, "platform": sys.platform,
               "original_policy": cfg.get("originals"),
               "original_manifest": file_hash(original) if original.exists() else None}
    if check["kind"] == "manual":
        payload["submission_policy"] = cfg.get("submission")
        payload["release_policy"] = cfg.get("release")
    return {"digest": digest(payload), **payload}


def git_info(root):
    def call(*args):
        try:
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None
    status = call("status", "--porcelain", "--", ".")
    return {"head": call("rev-parse", "HEAD"), "branch": call("branch", "--show-current"),
            "status": status, "dirty": bool(status) if status is not None else None,
            "note": "Git 정보는 보조 정보이며 검증 대상은 파일 지문으로 구분"}


def originals_status(root, cfg):
    policy = cfg.get("originals", {})
    if policy.get("mode") == "none":
        return {"status": "NOT_APPLICABLE" if policy.get("reason", "").strip() else "NOT_CONFIGURED", "reason": policy.get("reason", "")}
    if policy.get("mode") != "tracked":
        return {"status": "NOT_CONFIGURED", "reason": "원본 유무·경로를 분류하지 않음"}
    try:
        saved = load(safe_path(root, ORIGINALS, must_exist=True))
        if saved["paths"] != policy.get("paths"):
            raise HarnessError("원본 경로와 최초 목록 불일치")
        actual = collect(root, saved["paths"], ignore_generated=False)
        changed = sorted(k for k in set(actual) | set(saved["files"]) if actual.get(k) != saved["files"].get(k))
        return {"status": "FAIL" if changed else "PASS", "changed": changed, "files": len(actual)}
    except (HarnessError, KeyError) as exc:
        return {"status": "BLOCKED", "reason": str(exc)}


def originals_init(root, cfg):
    policy = cfg.get("originals", {})
    if policy.get("mode") != "tracked":
        raise HarnessError("checks.json의 originals.mode=tracked와 paths를 먼저 지정하세요")
    files = collect(root, policy.get("paths"), ignore_generated=False)
    write_new(safe_path(root, ORIGINALS), {"created_at": now(), "paths": policy["paths"], "files": files})
    return {"status": "BASELINE_CREATED", "files": len(files), "note": "최초 기준은 덮어쓰지 않음"}


def new_run(root):
    run_id = identifier()
    directory = safe_path(root, "artifacts/evidence/" + run_id)
    directory.mkdir(parents=True, exist_ok=False)
    return run_id, directory


def record(root, directory, result):
    write_new(directory / "result.json", result)
    index = safe_path(root, "docs/EVIDENCE.md")
    index.parent.mkdir(parents=True, exist_ok=True)
    link = "../" + (directory / "result.json").relative_to(root).as_posix()
    with index.open("a", encoding="utf-8") as out:
        out.write(f"\n- `{result['run_id']}` · `{result['check_id']}` · {result['category']} · **{result['status']}** · [실행 기록]({link})\n")
    return result


def child_process(command, cwd, logfile, timeout):
    started = time.monotonic()
    try:
        with logfile.open("wb") as output:
            proc = subprocess.Popen(command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                    start_new_session=(os.name == "posix"), env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            try:
                code = proc.wait(timeout=timeout)
                return code, "FINISHED", round(time.monotonic() - started, 3)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
                proc.wait()
                return None, "TIMEOUT", round(time.monotonic() - started, 3)
    except OSError as exc:
        logfile.write_text(str(exc), encoding="utf-8")
        return None, "BLOCKED", round(time.monotonic() - started, 3)


def run_check(root, marker, cfg, check):
    before = snapshot(root, marker, check)
    run_id, directory = new_run(root)
    result = {"version": VERSION, "run_id": run_id, "check_id": check["id"], "category": check["category"],
              "kind": check["kind"], "feature_ids": check["feature_ids"], "started_at": now(),
              "root": str(root), "expected": check["expected"], "snapshot": before, "git": git_info(root),
              "originals_before": originals_status(root, cfg), "exit_code": None, "counts": None,
              "command": None, "status": "PENDING", "observed": "아직 실행하지 않음"}
    if check["kind"] == "manual":
        result["observed"] = "사람 확인 대기. 이 실행 ID로 confirm하고 관찰 사실을 기록하세요"
        result["ended_at"] = now()
        return record(root, directory, result)
    if result["originals_before"]["status"] in {"FAIL", "BLOCKED"}:
        result.update(status="BLOCKED", observed="원본 상태 이상: 실행하지 않음", ended_at=now())
        return record(root, directory, result)
    cwd = safe_path(root, check.get("cwd", "."), must_exist=True, allow_root=True)
    if check["kind"] == "unittest":
        report = directory / "unittest.json"
        command = [sys.executable, str(Path(__file__).parent / "_unittest_runner.py"),
                   str(root), check.get("start_dir", "tests"), check.get("pattern", "test_*.py"), str(report), run_id]
    else:
        command = [sys.executable if item == "{python}" else item for item in check["command"]]
    fresh_before = {}
    for relative in check.get("fresh_files", []):
        path = safe_path(root, relative)
        fresh_before[relative] = (path.stat().st_mtime_ns, path.stat().st_size, file_hash(path)) if path.is_file() else None
    result.update(command=command, cwd=str(cwd))
    code, process_state, seconds = child_process(command, cwd, directory / "output.log", check.get("timeout_seconds", 60))
    result.update(exit_code=code, elapsed_seconds=seconds, log="artifacts/evidence/" + run_id + "/output.log")
    status, observed = "INCONCLUSIVE", "검사 결과를 판정하지 못함"
    if process_state in {"TIMEOUT", "BLOCKED"}:
        status, observed = process_state, "시간 초과" if process_state == "TIMEOUT" else "명령 실행 불가"
    elif check["kind"] == "unittest":
        if not report.exists():
            status, observed = "INCONCLUSIVE", "이번 실행의 unittest 결과 파일 없음"
        else:
            data = load(report)
            result["counts"] = data.get("counts")
            counts = data.get("counts", {})
            if data.get("run_id") != run_id:
                status, observed = "INCONCLUSIVE", "결과 실행 ID 불일치"
            elif counts.get("run", 0) == 0:
                status, observed = "UNVERIFIED", "실행한 테스트 0개"
            elif code != 0 or counts.get("failures", 0) or counts.get("errors", 0) or counts.get("unexpected_successes", 0):
                status, observed = "FAIL", "테스트 실패 또는 실행 오류"
            elif counts.get("skipped", 0) or counts.get("expected_failures", 0):
                status, observed = "INCOMPLETE", "건너뜀/예상 실패 항목이 남아 있음"
            else:
                status, observed = "PASS", f"실제 테스트 {counts['run']}개 통과"
    elif code != 0:
        status, observed = "FAIL", "명령이 오류 종료"
    else:
        output = (directory / "output.log").read_text(encoding="utf-8", errors="replace")
        missing = [s for s in check.get("stdout_contains", []) if s not in output]
        stale = []
        for relative, old in fresh_before.items():
            path = safe_path(root, relative)
            current = (path.stat().st_mtime_ns, path.stat().st_size, file_hash(path)) if path.is_file() else None
            if current is None or current == old:
                stale.append(relative)
        status = "FAIL" if missing else "INCONCLUSIVE" if stale else "PASS"
        observed = f"출력 조건 누락={missing}; 새로 생성·갱신되지 않은 산출물={stale}"
    try:
        after = snapshot(root, marker, check)
    except HarnessError as exc:
        after = {"digest": None}
        status, observed = "STALE", "실행 중 검증 대상이 사라지거나 변경됨: " + str(exc)
    result["originals_after"] = originals_status(root, cfg)
    if before["digest"] != after["digest"]:
        status, observed = "STALE", "실행 중 검증 대상이 변경됨"
    if result["originals_after"]["status"] in {"FAIL", "BLOCKED"}:
        status, observed = "FAIL", "검사 후 원본 데이터 상태 이상"
    result.update(status=status, observed=observed, ended_at=now(), after_digest=after["digest"])
    return record(root, directory, result)


def reports(root):
    base = safe_path(root, "artifacts/evidence")
    if not base.exists():
        return []
    values = []
    for path in base.glob("RUN-*/result.json"):
        safe_path(root, path.relative_to(root).as_posix())
        values.append(load(path))
    return sorted(values, key=lambda r: r["started_at"])


def current_status(root, marker, cfg):
    latest = {}
    for item in reports(root):
        latest[item["check_id"]] = item
    rows = []
    for check in cfg["checks"]:
        previous = latest.get(check["id"])
        status = "NOT_RUN"
        note = "실행 기록 없음"
        try:
            current = snapshot(root, marker, check)
            if previous:
                status = previous["status"] if previous["snapshot"]["digest"] == current["digest"] else "STALE"
                note = previous["observed"] if status != "STALE" else "검증 이후 대상·설정·도구가 변경됨"
        except HarnessError as exc:
            status, note = "BLOCKED", str(exc)
        rows.append({"id": check["id"], "category": check.get("category"), "status": status,
                     "run_id": previous["run_id"] if previous else None, "note": note})
    return {"status": "NOT_CONFIGURED" if not rows else "STATUS_ONLY", "checks": rows,
            "originals": originals_status(root, cfg), "note": "검사 통과와 전체 기능 완료는 별개"}


def confirm(root, marker, cfg, run_id, outcome, observer, observation):
    if not re.fullmatch(r"RUN-[0-9TZ]+-[a-f0-9]{8}", run_id):
        raise HarnessError("잘못된 실행 ID")
    previous = load(safe_path(root, f"artifacts/evidence/{run_id}/result.json", must_exist=True))
    check = find_check(cfg, previous["check_id"])
    if check["kind"] != "manual" or previous["status"] != "PENDING":
        raise HarnessError("manual run으로 만든 확인 대기 기록만 확인 가능")
    if not observer.strip() or not observation.strip():
        raise HarnessError("확인자와 실제 관찰 내용을 입력하세요")
    current = snapshot(root, marker, check)
    new_id, directory = new_run(root)
    result = {**previous, "run_id": new_id, "started_at": now(), "ended_at": now(), "parent_run": run_id,
              "observer": observer, "observation_source": "reported-by-caller", "observed": observation,
              "status": "PASS" if outcome == "pass" else "FAIL", "git": git_info(root)}
    if current["digest"] != previous["snapshot"]["digest"]:
        result.update(status="STALE", observed="확인 대기 이후 코드 변경. 새 run으로 다시 확인하세요")
    result["originals_after"] = originals_status(root, cfg)
    if result["originals_after"]["status"] in {"FAIL", "BLOCKED"}:
        result.update(status="FAIL", observed="원본 상태 이상")
    return record(root, directory, result)


def sandbox_new(root, marker):
    run_id = identifier("TMP")
    path = safe_path(root, "work/runs/" + run_id)
    path.mkdir(parents=True, exist_ok=False)
    write_new(path / ".harness-owned.json", {"project_id": marker["project_id"], "run_id": run_id})
    return {"status": "CREATED", "id": run_id, "path": str(path)}


def sandbox_clean(root, marker, run_id):
    if not re.fullmatch(r"TMP-[0-9TZ]+-[a-f0-9]{8}", run_id):
        raise HarnessError("생성된 TMP 실행 ID만 초기화 가능")
    path = safe_path(root, "work/runs/" + run_id, must_exist=True)
    owned = load(safe_path(root, f"work/runs/{run_id}/.harness-owned.json", must_exist=True))
    if owned != {"project_id": marker["project_id"], "run_id": run_id}:
        raise HarnessError("다른 프로젝트 또는 소유권 불일치")
    for child in path.rglob("*"):
        safe_path(root, child.relative_to(root).as_posix())
    shutil.rmtree(path)
    return {"status": "REMOVED", "id": run_id}


def inventory(root, cfg):
    submission = cfg.get("submission", {})
    files = collect(root, submission.get("include"))
    excluded = submission.get("exclude", [])
    files = {k: v for k, v in files.items() if not any(k == p.rstrip("/") or k.startswith(p.rstrip("/") + "/") for p in excluded)}
    if not files:
        raise HarnessError("제출 대상이 비어 있음")
    missing = [p for p in submission.get("required_files", []) if p not in files]
    if not submission.get("required_files") or missing:
        raise HarnessError(f"필수 제출 파일 미설정 또는 누락: {missing}")
    dangerous = []
    for name in files:
        p = Path(name)
        if (p.name == ".env" or p.name.startswith(".env.") and p.name != ".env.example"
                or p.name in {"auth.json", "credentials.json"} or p.suffix in {".pem", ".key"}
                or name.startswith(("work/", ".git/"))):
            dangerous.append(name)
            continue
        data = (root / name).read_bytes()
        if re.search(br"(?m)^-----BEGIN (?:RSA )?PRIVATE KEY-----\r?$", data):
            dangerous.append(name)
    if dangerous:
        raise HarnessError(f"제출 제외·검토가 필요한 파일: {dangerous}")
    return files


def release(root, marker, cfg):
    state = current_status(root, marker, cfg)
    rows = {row["id"]: row for row in state["checks"]}
    reasons = []
    policy = cfg.get("release", {})
    required = policy.get("required_checks", [])
    if not required:
        reasons.append("필수 제품 검사 목록이 없음")
    for cid in required:
        if cid not in rows or rows[cid]["category"] != "task" or rows[cid]["status"] != "PASS":
            reasons.append(f"필수 실제 과제 검사 미통과: {cid}")
    review = policy.get("manual_review_check")
    if review not in required or not review:
        reasons.append("요구사항·최종 화면·제출 범위를 확인할 수동 검사가 없음")
    elif find_check(cfg, review)["kind"] != "manual":
        reasons.append("최종 검토는 manual 확인이어야 함")
    if state["originals"]["status"] not in {"PASS", "NOT_APPLICABLE"}:
        reasons.append("원본 보존 상태 미확정 또는 이상")
    try:
        files = inventory(root, cfg)
    except HarnessError as exc:
        files = {}
        reasons.append(str(exc))
    # Manual review must bind the actual submission inventory, not just one source file.
    if review and review in rows and files:
        try:
            reviewed = snapshot(root, marker, find_check(cfg, review))["files"]
            omitted = [p for p in files if p not in RECORDS and not p.startswith("artifacts/evidence/") and reviewed.get(p) != files[p]]
            if omitted:
                reasons.append(f"최종 검토 scope에 제출 파일이 빠짐: {omitted}")
        except HarnessError as exc:
            reasons.append(str(exc))
    return {"status": "READY_FOR_SUBMISSION" if not reasons else "NOT_READY", "reasons": reasons,
            "inventory": files, "inventory_digest": digest(files), "checks": state["checks"],
            "note": "로컬 설정 기준 점검. 공식 제출 완료·화면 자동 확인·비밀정보 완전 탐지를 뜻하지 않음"}


def doctor(root):
    root, marker, cfg = context(root)
    issues = []
    for check in cfg["checks"]:
        try:
            snapshot(root, marker, check)
        except HarnessError as exc:
            issues.append({"id": check["id"], "issue": str(exc)})
    return {"status": "BLOCKED" if issues else "ENVIRONMENT_ONLY", "version": VERSION,
            "root": str(root), "python": sys.version.split()[0], "git": git_info(root),
            "configured_checks": len(cfg["checks"]), "issues": issues,
            "originals": originals_status(root, cfg), "auto_skill_detection": "NOT_VERIFIED",
            "note": "파일·환경 확인만 수행. 제품 검증과 Codex 지침 자동 인식은 확인하지 않음"}
