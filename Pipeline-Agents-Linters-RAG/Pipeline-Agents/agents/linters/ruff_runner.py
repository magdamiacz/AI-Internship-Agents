import os
import subprocess


def run_ruff(output_dir: str) -> str:
    """
    Uruchamia ruff check na katalogu backend/ projektu.
    Konfiguracja czytana z output_dir/lint/ruff.toml (jeśli istnieje),
    z fallbackiem na output_dir/backend/ruff.toml.
    Zwraca wynik jako string z nagłówkiem Markdown.
    """
    backend_path = os.path.join(output_dir, "backend")
    if not os.path.isdir(backend_path):
        return ""

    # Szukamy konfiguracji najpierw w lint/, potem w backend/
    lint_config = os.path.join(output_dir, "lint", "ruff.toml")
    backend_config = os.path.join(output_dir, "backend", "ruff.toml")

    cmd = ["ruff", "check", backend_path, "--output-format=concise"]
    if os.path.exists(lint_config):
        cmd += ["--config", lint_config]
    elif os.path.exists(backend_config):
        cmd += ["--config", backend_config]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = (r.stdout or r.stderr or "").strip()
        return f"### Python (ruff)\n{out if out else 'Brak błędów.'}"
    except FileNotFoundError:
        return "### Python (ruff)\nRuff nie jest zainstalowany (pip install ruff)."
    except Exception as e:
        return f"### Python (ruff)\nBłąd: {e}"
