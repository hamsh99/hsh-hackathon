#!/usr/bin/env python3
"""Run checks with evidence. Exit 0 is scoped success, never automatic submission."""
import argparse
import json
import sys
sys.dont_write_bytecode = True
from _core import (HarnessError, context, find_check, run_check, current_status,
                   confirm, originals_init, originals_status, sandbox_new, sandbox_clean, release)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--verbose", action="store_true", help="파일별 지문을 포함한 전체 JSON 출력")
    sub = parser.add_subparsers(dest="action", required=True)
    run = sub.add_parser("run", help="실제 등록된 검사 하나 실행")
    run.add_argument("check_id")
    sub.add_parser("status", help="현재 파일 지문과 실행 기록 비교")
    manual = sub.add_parser("confirm", help="사람이 관찰한 사실을 기록; 자동 UI 검사가 아님")
    manual.add_argument("run_id")
    manual.add_argument("--result", required=True, choices=["pass", "fail"])
    manual.add_argument("--observer", required=True)
    manual.add_argument("--observation", required=True)
    original = sub.add_parser("originals")
    original.add_argument("operation", choices=["init", "verify"])
    sandbox = sub.add_parser("sandbox")
    sandbox.add_argument("operation", choices=["new", "clean"])
    sandbox.add_argument("run_id", nargs="?")
    sub.add_parser("release", help="최종 점검만 수행. 업로드·배포·커밋하지 않음")
    args = parser.parse_args()
    try:
        root, marker, cfg = context(args.root)
        if args.action == "run":
            result = run_check(root, marker, cfg, find_check(cfg, args.check_id))
        elif args.action == "status":
            result = current_status(root, marker, cfg)
        elif args.action == "confirm":
            result = confirm(root, marker, cfg, args.run_id, args.result, args.observer, args.observation)
        elif args.action == "originals":
            result = originals_init(root, cfg) if args.operation == "init" else originals_status(root, cfg)
        elif args.action == "sandbox":
            result = sandbox_new(root, marker) if args.operation == "new" else sandbox_clean(root, marker, args.run_id or "")
        else:
            result = release(root, marker, cfg)
    except (HarnessError, OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
    display = dict(result)
    if not args.verbose and "snapshot" in display:
        display["snapshot"] = {"digest": result["snapshot"]["digest"], "file_count": len(result["snapshot"]["files"])}
        display["record_path"] = "artifacts/evidence/" + result["run_id"] + "/result.json"
    print(json.dumps(display, ensure_ascii=False, indent=2))
    success = {"PASS", "BASELINE_CREATED", "NOT_APPLICABLE", "CREATED", "REMOVED", "READY_FOR_SUBMISSION"}
    if result["status"] == "STATUS_ONLY":
        return 0 if all(r["status"] == "PASS" for r in result["checks"]) and result["originals"]["status"] in {"PASS", "NOT_APPLICABLE"} else 2
    return 0 if result["status"] in success else 1 if result["status"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
