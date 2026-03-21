import subprocess
import sys
from pathlib import Path

EXCLUDE = {
    Path("src/saferaise/_version.py"),
}


def get_files() -> list[str]:
    """Get all Python files to process.

    Returns:
        List of file paths as strings.
    """
    files = [str(p) for p in Path("src").rglob("*.py") if p not in EXCLUDE]
    files += [str(p) for p in Path("tests").rglob("*.py")]
    return files


def main() -> None:
    """Run pyupgrade on all Python files except excluded ones."""
    check_mode = "--check" in sys.argv
    files = get_files()

    if not files:
        print("No files to process.")
        sys.exit(0)

    if check_mode:
        originals = {f: Path(f).read_text(encoding="utf-8") for f in files}
        subprocess.run(["pyupgrade", "--py313-plus", *files], check=False)  # noqa: S603, S607

        changed = [f for f in files if Path(f).read_text(encoding="utf-8") != originals[f]]

        for f, content in originals.items():
            Path(f).write_text(content, encoding="utf-8")

        if changed:
            print("pyupgrade would reformat the following files:")
            for f in changed:
                print(f"  {f}")
            sys.exit(1)
    else:
        subprocess.run(["pyupgrade", "--py313-plus", *files], check=True)  # noqa: S603, S607


if __name__ == "__main__":
    main()