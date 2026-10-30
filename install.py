#!/usr/bin/env python3
"""Preview first; --apply copies missing harness files without Git/global changes."""
from __future__ import annotations
import argparse
import json
import sys
import uuid
from pathlib import Path
sys.dont_write_bytecode = True

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE / "tools"))
from _core import HarnessError, safe_path


def install(destination, apply=False):
    target = Path(destination).absolute()
    # System aliases such as macOS /tmp may resolve normally; reject a linked target itself.
    if target.is_symlink():
        raise HarnessError("설치 대상이 링크입니다. 실제 경로를 지정하세요")
    target = target.resolve()
    if not target.is_dir() or target == SOURCE or target.is_relative_to(SOURCE):
        raise HarnessError("기존 과제 폴더를 지정하세요. 하네스 원본 안에는 설치하지 않습니다")
    mapping = {
        "harness/OPERATIONS.md": "harness/OPERATIONS.md",
        "harness/CONFIG_GUIDE.md": "harness/CONFIG_GUIDE.md",
        "harness/START.md": "harness/START.md",
        "harness/RELEASE_CHECKLIST.md": "harness/RELEASE_CHECKLIST.md",
        "tools/doctor.py": "tools/doctor.py", "tools/check.py": "tools/check.py",
        "tools/_core.py": "tools/_core.py", "tools/_unittest_runner.py": "tools/_unittest_runner.py",
        "templates/checks.json": "harness/checks.json",
        "templates/README.md": "README.md",
        "templates/gitignore.suggested": "harness/gitignore.suggested",
    }
    for name in ("TASK", "STATE", "DECISIONS", "EVIDENCE"):
        mapping[f"templates/docs/{name}.md"] = f"docs/{name}.md"
    agent = safe_path(target, "AGENTS.md")
    mapping["AGENTS.md"] = "harness/AGENTS.suggested.md" if agent.exists() else "AGENTS.md"
    preserve = {"README.md", "harness/checks.json", "harness/project.json", "docs/TASK.md",
                "docs/STATE.md", "docs/DECISIONS.md", "docs/EVIDENCE.md"}
    payloads = []
    for source, dest in mapping.items():
        payloads.append((dest, (SOURCE / source).read_bytes()))
    payloads.append(("harness/project.json", (json.dumps({"version": 1, "project_id": uuid.uuid4().hex}, indent=2) + "\n").encode()))
    changes = []
    for relative, data in payloads:
        path = safe_path(target, relative)
        if path.exists():
            if not path.is_file():
                action = "CONFLICT"
            elif relative in preserve:
                action = "PRESERVE"
            else:
                action = "UNCHANGED" if path.read_bytes() == data else "CONFLICT"
        else:
            action = "CREATE"
        changes.append({"path": relative, "action": action})
    if any(row["action"] == "CONFLICT" for row in changes):
        return {"status": "CONFLICT", "target": str(target), "changes": changes,
                "note": "아무 파일도 쓰지 않았습니다. 다른 파일을 덮어쓰지 마세요"}
    if apply:
        for (relative, data), row in zip(payloads, changes):
            if row["action"] == "CREATE":
                path = safe_path(target, relative)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as out:
                    out.write(data)
    return {"status": "APPLIED" if apply else "PREVIEW", "target": str(target), "changes": changes,
            "existing_agents": agent.exists() and mapping["AGENTS.md"] != "AGENTS.md",
            "note": "Git·전역 설정·기존 파일은 변경하지 않음. 스킬 자동 인식 확인은 별도. START.md를 읽으세요"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = install(args.destination, args.apply)
    except (HarnessError, OSError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] in {"BLOCKED", "CONFLICT"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
