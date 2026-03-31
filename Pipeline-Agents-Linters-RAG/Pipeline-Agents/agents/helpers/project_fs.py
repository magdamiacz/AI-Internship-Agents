import os
from typing import Dict, List, Tuple

EXCLUDE_DIRS = {"images", "__pycache__", ".git", ".venv", ".ruff_cache"}
EXCLUDE_EXTS = {".db", ".png", ".jpg", ".pyc"}
EXCLUDE_FILES = {"pipeline_state.json"}


def walk_text_files(
    output_dir: str,
    extensions: Tuple[str, ...] = (".py", ".html"),
    exclude_dirs: set = EXCLUDE_DIRS,
) -> List[Tuple[str, str]]:
    """Zwraca listę (rel_path, full_path) dla plików o podanych rozszerzeniach."""
    result = []
    for root, dirs, files in os.walk(output_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for filename in files:
            if filename.endswith(extensions):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, output_dir).replace("\\", "/")
                result.append((rel_path, full_path))
    return result


def load_existing_project_files(output_dir: str) -> Dict[str, str]:
    """Wczytuje wszystkie pliki tekstowe projektu do słownika {rel_path: content}."""
    existing_files: Dict[str, str] = {}
    for root, dirs, files in os.walk(output_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for filename in files:
            if filename in EXCLUDE_FILES:
                continue
            if any(filename.endswith(ext) for ext in EXCLUDE_EXTS):
                continue
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, output_dir).replace("\\", "/")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    existing_files[rel_path] = f.read()
            except Exception:
                pass
    return existing_files
