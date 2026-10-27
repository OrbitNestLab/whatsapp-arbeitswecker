from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "output"}
TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".example", ".txt", ""}
PATTERNS = {
    "OpenAI-Schlüssel": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "GitHub-Token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "Meta-Zugriffstoken": re.compile(r"\bEA[A-Za-z0-9]{30,}"),
    "Private-Key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"Dockerfile", ".gitignore"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: möglicher {label}")
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Keine typischen Zugangsdatenmuster gefunden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
