"""Private subprocess runner; writes only this run's machine-readable counts."""
import json
import sys
import unittest
from pathlib import Path


def main():
    root, start, pattern, destination, run_id = sys.argv[1:]
    sys.path.insert(0, root)
    loader = unittest.TestLoader()
    suite = loader.discover(str(Path(root) / start), pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    counts = {"run": result.testsRun, "skipped": len(result.skipped),
              "failures": len(result.failures), "errors": len(result.errors),
              "expected_failures": len(result.expectedFailures),
              "unexpected_successes": len(result.unexpectedSuccesses)}
    with open(destination, "x", encoding="utf-8") as out:
        json.dump({"run_id": run_id, "counts": counts}, out)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
