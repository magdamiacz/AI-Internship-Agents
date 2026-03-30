import os
import subprocess
import sys


def run_htmlhint(output_dir: str) -> str:
    """
    Uruchamia htmlhint na frontend/index.html projektu.
    Konfiguracja czytana z output_dir/lint/.htmlhintrc (jeśli istnieje).
    Na Windows używa shell=True (obejście dla npx w PowerShell/CMD).
    Zwraca wynik jako string z nagłówkiem Markdown.
    """
    html_path = os.path.join(output_dir, "frontend", "index.html")
    if not os.path.exists(html_path):
        return ""

    lint_config = os.path.join(output_dir, "lint", ".htmlhintrc")
    config_flag = f'--config "{lint_config}"' if (sys.platform == "win32" and os.path.exists(lint_config)) else ""
    config_args = ["--config", lint_config] if (sys.platform != "win32" and os.path.exists(lint_config)) else []

    try:
        if sys.platform == "win32":
            cmd_str = f'npx --yes htmlhint "{html_path}"'
            if config_flag:
                cmd_str += f" {config_flag}"
            r = subprocess.run(
                cmd_str,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
            )
        else:
            cmd = ["npx", "--yes", "htmlhint", html_path] + config_args
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        out = (r.stdout or r.stderr or "").strip()
        return f"### HTML (htmlhint)\n{out if out else 'Brak błędów.'}"
    except FileNotFoundError:
        return "### HTML (htmlhint)\nNode.js/npx nie jest dostępne."
    except subprocess.TimeoutExpired:
        return "### HTML (htmlhint)\nPrzekroczono limit czasu."
    except Exception as e:
        return f"### HTML (htmlhint)\nBłąd: {e}"
