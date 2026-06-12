from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def must_exist(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing required frontend file: {path}")


def must_contain(path: Path, snippet: str) -> None:
    content = path.read_text(encoding="utf-8")
    if snippet not in content:
        raise SystemExit(f"Expected to find {snippet!r} in {path}")


def main() -> None:
    for name in [
        "index.html",
        "trans.html",
        "emails-demo.html",
        "script.js",
        "config.js",
        "config.example.js",
        "README.md",
    ]:
        must_exist(FRONTEND / name)

    must_contain(FRONTEND / "trans.html", 'src="config.js"')
    must_contain(FRONTEND / "trans.html", 'src="script.js"')
    must_contain(FRONTEND / "config.example.js", "window.LEXAI_API_BASE")
    must_contain(FRONTEND / "script.js", "window.LEXAI_API_BASE")
    must_contain(FRONTEND / "script.js", "/healthz")


if __name__ == "__main__":
    main()
