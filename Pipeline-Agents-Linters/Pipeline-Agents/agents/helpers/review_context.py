import os
from typing import Tuple

EXCLUDE_DIRS = {"images", "__pycache__", ".git", ".venv", ".ruff_cache"}
MAX_FILES = 8
MAX_CHARS_PER_FILE = 3000


def build_review_code_context(output_dir: str) -> str:
    """
    Zbiera fragmenty plików .py i .html z projektu do kontekstu dla agenta review.
    Limit: MAX_FILES plików, MAX_CHARS_PER_FILE znaków na plik.
    """
    code_files: list[Tuple[str, str]] = []
    for root, dirs, files in os.walk(output_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for filename in files:
            if filename.endswith((".py", ".html")):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, output_dir).replace("\\", "/")
                code_files.append((rel_path, full_path))

    project_code_ctx = ""
    for rel_path, full_path in code_files[:MAX_FILES]:
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            project_code_ctx += f"\n\n=== {rel_path} ===\n{content[:MAX_CHARS_PER_FILE]}"
        except Exception:
            pass

    return project_code_ctx


def load_readme_context(readme_path: str, output_dir: str) -> str:
    """Wczytuje README z docs/ albo fallback z katalogu projektu."""
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    fallback = os.path.join(output_dir, "README.md")
    if os.path.exists(fallback):
        with open(fallback, "r", encoding="utf-8") as f:
            return f.read()
    return ""
