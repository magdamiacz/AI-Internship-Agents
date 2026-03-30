# Refaktoryzacja pipeline: prompty, helpers, lintery i Culinary-App/lint

Ten dokument opisuje zmiany w projekcie **Pipeline-Agents** oraz powiązany katalog **Culinary-App/lint/**: co zostało zrobione, jak to jest zorganizowane i jak to działa w czasie działania pipeline.

---

## 1. Cel refaktoryzacji

Wcześniej większość logiki agentów (prompty inline, odczyt plików, parsowanie JSON, zapis plików, uruchamianie linterów) znajdowała się w jednym dużym pliku `agents/nodes.py`. Refaktoryzacja rozdziela odpowiedzialności na:

1. **Prompty** — same teksty i funkcje `build_*` bez importów LLM.
2. **Funkcje pomocnicze** — stan pipeline, system plików, parsowanie odpowiedzi modelu, zapis plików, kontekst do code review.
3. **Lintery** — kod uruchamiający Ruff i HTMLHint w pakiecie `agents/linters/`, z konfiguracją leżącą w projekcie docelowym (**Culinary-App**).
4. **Cienki `agents/nodes.py`** — węzły LangGraph tylko składają prompty, wołają helpery i `llm.invoke(...)`.

Import w `main.py` pozostaje bez zmian: `from agents.nodes import ...`.

---

## 2. Nowa struktura katalogów (Pipeline-Agents)

| Ścieżka | Rola |
|---------|------|
| `agents/nodes.py` | Węzły grafu (`load_project_node`, `supervisor_node`, agenci, `save_and_proceed_node`). Importuje prompty, helpers i `run_all_linters`. |
| `agents/prompts/` | Moduły z funkcjami `build_*` zwracającymi stringi promptów (`supervisor`, `task`, `arch`, `tech`, `coder`, `review`, `docker`). |
| `agents/helpers/` | Logika pomocnicza bez bezpośredniego wywoływania modelu. |
| `agents/linters/` | Uruchamianie Ruff i HTMLHint oraz agregacja wyników. |
| `agents/state.py` | Bez zmian — definicja `AgentState` dla LangGraph. |
| `main.py` | Bez zmian — budowa grafu i pętla CLI. |

---

## 3. Moduł `agents/prompts/`

**Zasada:** w plikach promptów nie importuje się klientów LLM — tylko tekst i formatowanie (`f-string`, `str.format`).

| Plik | Funkcje / treść |
|------|-----------------|
| `supervisor.py` | `build_supervisor_prompt(phase)` — delegacja do aktualnej fazy. |
| `task.py` | `build_task_prompt()` — specyfikacja MVP. |
| `arch.py` | `build_arch_prompt(task_ctx)` — architektura na podstawie taska. |
| `tech.py` | `build_tech_prompt(task_ctx, arch_ctx)` — uzasadnienie stacku. |
| `coder.py` | `build_coder_prompt_modify(...)`, `build_coder_prompt_create(...)` oraz stała `FEEDBACK_SUFFIX` dla uwag użytkownika. |
| `review.py` | `build_review_prompt(readme_ctx, project_code_ctx, linter_output)` — audyt kodu z wynikami linterów. |
| `docker.py` | `build_docker_prompt(readme_ctx)` — pliki Docker w JSON. |

Węzły w `nodes.py` tylko wczytują kontekst z plików (`task_file`, `arch_file`, itd.) i przekazują go do tych funkcji.

---

## 4. Moduł `agents/helpers/`

| Plik | Odpowiedzialność |
|------|------------------|
| `pipeline_state.py` | `ALL_PHASES`, `update_pipeline_state(output_dir, phase)` — zapis i aktualizacja `pipeline_state.json` w katalogu projektu (nazwa projektu, ukończone fazy, ostatnia faza). |
| `project_fs.py` | `load_existing_project_files(output_dir)` — odczyt plików tekstowych przy starcie w trybie MODIFY (z wykluczeniami: `images`, `__pycache__`, `.git`, bazy, obrazy, `pipeline_state.json`). `walk_text_files(...)` — pomocniczo lista plików `.py`/`.html`. |
| `json_from_llm.py` | `parse_json_from_llm(content)` — usuwa opcjonalne bloki ` ```json `, wycina pierwszy obiekt `{...}` i parsuje JSON; zwraca `dict` lub `None`. Używane w fazach **code** i **docker** w `save_and_proceed_node`. |
| `file_write.py` | `write_files_safely(data_dict, base_path, mode)` — rekurencyjny zapis; w trybie `modify` pomija pliki bez zmian treści. |
| `review_context.py` | `load_readme_context(readme_path, output_dir)` — README z `docs/` lub fallback `README.md` w projekcie. `build_review_code_context(output_dir)` — fragmenty do ~8 plików `.py`/`.html` z limitem znaków na plik. |

---

## 5. Moduł `agents/linters/` i przepływ danych

| Plik | Działanie |
|------|-----------|
| `ruff_runner.py` | `run_ruff(output_dir)` — jeśli istnieje `output_dir/backend`, uruchamia `ruff check` na tym katalogu. Konfiguracja: **`output_dir/lint/ruff.toml`** (priorytet), w przeciwnym razie **`output_dir/backend/ruff.toml`**. Wynik to jeden blok tekstu z nagłówkiem `### Python (ruff)`. |
| `htmlhint_runner.py` | `run_htmlhint(output_dir)` — jeśli istnieje `frontend/index.html`, uruchamia `npx htmlhint` z opcjonalnym **`--config`** wskazującym na **`output_dir/lint/.htmlhintrc`**. Na Windows używane jest `shell=True` dla kompatybilności z `npx`. |
| `run_all.py` | `run_all_linters(output_dir)` — łączy wyniki Ruff i HTMLHint w jeden string (oddzielone podwójnymi newline); jeśli nic do sprawdzenia — komunikat informacyjny. |

**Faza review:** `review_agent_node` w `nodes.py` wywołuje `run_all_linters(output_dir)` i wkleja wynik do `build_review_prompt(...)`, więc model widzi realne ostrzeżenia linterów przy pisaniu raportu Code Review.

---

## 6. Culinary-App: folder `lint/` (konfiguracja w repozytorium docelowym)

Konfiguracje nie są „generowane” przez pipeline w sensie runtime — są **częścią repozytorium Culinary-App** i pipeline tylko je **odczytuje** przez `--config`.

| Ścieżka | Zawartość |
|---------|-----------|
| `Culinary-App/lint/ruff.toml` | Jedno źródło prawdy dla Ruff (długość linii, reguły E/F/W/I itd.). |
| `Culinary-App/lint/.htmlhintrc` | Reguły HTMLHint (np. małe litery w tagach/atrybutach). |
| `Culinary-App/lint/README.md` | Krótki opis i przykładowe komendy ręcznego uruchomienia linterów. |
| `Culinary-App/backend/ruff.toml` | Zastąpiony wskazówką, że pełna konfiguracja jest w `../lint/ruff.toml` (uniknięcie rozjazdów dwóch pełnych plików). |

**Wymaganie:** `output_dir` wskazany w pipeline musi być katalogiem głównym projektu (ten sam poziom co `backend/`, `frontend/`, `lint/`), żeby ścieżki `lint/ruff.toml` i `lint/.htmlhintrc` były poprawne.

---

## 7. Jak to działa krok po kroku (uproszczony przepływ)

1. **Uruchomienie:** `python main.py` z katalogu `Pipeline-Agents` — graf LangGraph jak wcześniej.
2. **load_project:** odczyt lub brak projektu — tryb CREATE vs MODIFY; w MODIFY pliki przez `load_existing_project_files`.
3. **Agenci task → arch → tech:** prompty z `agents/prompts/`, zapis szkiców przez `save_and_proceed_node` do `docs/`.
4. **coder:** prompt z `coder.py`; zapis wygenerowanego JSON-a z kodem przez `parse_json_from_llm` + `write_files_safely` do `output_dir`.
5. **review:** README + fragmenty kodu z `review_context` + **`run_all_linters(output_dir)`** → jeden prompt w `review.py` → raport w `docs/code_review.md` (po akceptacji użytkownika).
6. **docker:** analogicznie parsowanie JSON i zapis plików w `docker/`; opcjonalnie `docker-compose up`.
7. **Po każdej zakończonej fazie z listy:** `update_pipeline_state` aktualizuje `pipeline_state.json` w katalogu projektu.

---

## 8. Podsumowanie korzyści

- **Łatwiejsze utrzymanie:** zmiana treści promptu bez przeszukiwania setek linii w jednym pliku.
- **Testowalność:** helpery i (w razie potrzeby) parser JSON można wywoływać izolowanie.
- **Spójność linterów:** jeden katalog `Culinary-App/lint/` dla narzędzi CLI i dla pipeline w fazie review.
- **Stabilny kontrakt:** `from agents.nodes import ...` w `main.py` bez zmian.

---

*Dokument opisuje stan po refaktoryzacji zgodnie z planem „Refaktoryzacja pipeline: prompty, helpers, lintery + Culinary-App/lint”.*
