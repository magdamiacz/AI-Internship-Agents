# Konfiguracje linterów

Ten folder zawiera wspólne pliki konfiguracyjne dla narzędzi do statycznej analizy kodu projektu Culinary-App.

## Pliki

| Plik | Narzędzie | Zakres |
|------|-----------|--------|
| `ruff.toml` | [Ruff](https://docs.astral.sh/ruff/) | `backend/` (Python) |
| `.htmlhintrc` | [HTMLHint](https://htmlhint.com/) | `frontend/index.html` (HTML) |

## Użycie ręczne

```bash
# Python (z katalogu głównego Culinary-App)
ruff check backend --config lint/ruff.toml

# HTML (Node.js wymagany)
npx htmlhint frontend/index.html --config lint/.htmlhintrc
```

## Uwaga

Pipeline `Pipeline-Agents` uruchamia te lintery automatycznie podczas fazy **review** i przekazuje wyniki do agenta Code Review jako kontekst.
