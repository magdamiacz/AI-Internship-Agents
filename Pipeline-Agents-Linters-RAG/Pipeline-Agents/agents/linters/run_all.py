from agents.linters.ruff_runner import run_ruff
from agents.linters.htmlhint_runner import run_htmlhint


def run_all_linters(output_dir: str) -> str:
    """
    Uruchamia wszystkie lintery (Ruff, htmlhint) i zwraca zagregowany wynik jako string.
    Pusty wynik oznacza brak plików do sprawdzenia.
    """
    results = []

    ruff_result = run_ruff(output_dir)
    if ruff_result:
        results.append(ruff_result)

    htmlhint_result = run_htmlhint(output_dir)
    if htmlhint_result:
        results.append(htmlhint_result)

    return "\n\n".join(results) if results else "Brak plików do sprawdzenia."
