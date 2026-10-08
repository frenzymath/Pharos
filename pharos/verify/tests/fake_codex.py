#!/usr/bin/env python3
"""Deterministic Codex stub for verification tests.

Reads the prompt from stdin when the final argument is "-", otherwise from
the final argument. Writes a wrong verdict for the marker ``[[FAKE:wrong]]``
and a correct verdict otherwise. It does not evaluate mathematics.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("fake_codex: no prompt argument\n")
        return 2
    # the real launcher passes "-" and pipes the prompt on stdin
    prompt = sys.stdin.read() if sys.argv[-1] == "-" else sys.argv[-1]

    m = re.search(r"this exact path:\s*(\S+)", prompt)
    if not m:
        sys.stderr.write("fake_codex: could not find output path in prompt\n")
        return 3
    out_path = Path(m.group(1).rstrip("."))

    if "[[FAKE:wrong]]" in prompt:
        payload = {
            "verification_report": {
                "summary": "FAKE stub verdict (plumbing test): marker [[FAKE:wrong]] present.",
                "critical_errors": [
                    {"location": "proof", "issue": "fake_codex injected critical error for the reject path"}
                ],
                "gaps": [],
            },
            "verdict": "wrong",
            "repair_hints": "This is a fake reject from fake_codex.py (plumbing only).",
        }
    else:
        payload = {
            "verification_report": {
                "summary": "FAKE stub verdict (plumbing test): no error marker; accepting.",
                "critical_errors": [],
                "gaps": [],
            },
            "verdict": "correct",
            "repair_hints": "",
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    sys.stdout.write(f"fake_codex: wrote {payload['verdict']} verdict to {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
