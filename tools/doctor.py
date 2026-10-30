#!/usr/bin/env python3
"""Read-only environment report; does not certify product behavior."""
import argparse
import json
import sys
sys.dont_write_bytecode = True
from _core import HarnessError, doctor

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", default=".")
args = parser.parse_args()
try:
    result = doctor(args.root)
except (HarnessError, OSError, ValueError) as exc:
    result = {"status": "BLOCKED", "reason": str(exc)}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(2 if result["status"] == "BLOCKED" else 0)
