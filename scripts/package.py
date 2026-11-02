"""Create the downloadable source/build bundle without recursive archives or local data."""
import argparse
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git", ".venv", ".cache", "node_modules", "__pycache__", ".local",
    ".pytest_cache", "test-results", "playwright-report", "downloads",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "downloads/3DAS-Letter-Maker.zip")
    args = parser.parse_args()
    output = args.output.resolve()
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise SystemExit("Najpierw zbuduj frontend: npm --prefix frontend run build")
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, directories, files in os.walk(ROOT):
            directories[:] = sorted(d for d in directories if d not in EXCLUDED)
            for name in sorted(files):
                path = Path(folder) / name
                if path.is_symlink() or path.resolve() == output or name == ".env" or name.startswith(".env.") or name.endswith((".tsbuildinfo", ".pyc", ".log")):
                    continue
                z.write(path, Path("3DAS-Letter-Maker") / path.relative_to(ROOT))
                count += 1
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:
            raise SystemExit("Weryfikacja ZIP nie powiodla sie.")
        assert "3DAS-Letter-Maker/scripts/tools.ps1" in z.namelist()
    print(f"ZIP: {output.name}, {count} plikow, {output.stat().st_size} bajtow")


if __name__ == "__main__":
    main()
