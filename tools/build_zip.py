#!/usr/bin/env python3
"""Build the installable archive: ``dist/subdiv-<version>.zip``.

IngeTrazo installs a zip that holds exactly ONE package folder with an
``__init__.py``. The archive is deterministic (sorted names, fixed dates), so
the same sources always give the same SHA-256, the value the catalog entry
needs. Run it from the repository root:  python tools/build_zip.py
"""
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "subdiv"
STAMP = (2026, 1, 1, 0, 0, 0)


def main() -> None:
    version = re.search(r'__version__ = "([^"]+)"',
                        (PACKAGE / "__init__.py").read_text(encoding="utf-8")).group(1)
    out = ROOT / "dist" / f"subdiv-{version}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PACKAGE.glob("*.py")):
            info = zipfile.ZipInfo(f"subdiv/{path.name}", STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size} bytes")
    print(f"sha256 = \"{digest}\"")


if __name__ == "__main__":
    main()
