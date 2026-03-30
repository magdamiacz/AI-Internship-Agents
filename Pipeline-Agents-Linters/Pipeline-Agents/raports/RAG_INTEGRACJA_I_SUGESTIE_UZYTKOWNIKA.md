# RAG w pipeline + sugestie użytkownika

Ten dokument opisuje zmiany: integrację uproszczonego **RAG** (Retrieval Augmented Generation) wg wzorca z [LangChain — Build a RAG agent](https://docs.langchain.com/oss/python/langchain/rag), oraz sposób **wprowadzania wskazówek** przed uruchomieniem i w trakcie pracy z agentami.

---

## 1. Co zostało dodane

### 1.1 Moduł `agents/rag/`

| Plik | Rola |
|------|------|
| [agents/rag/project_rag.py](agents/rag/project_rag.py) | Indeksowanie projektu docelowego (`output_dir`) i retrieval semantyczny. |
| [agents/rag/__init__.py](agents/rag/__init__.py) | Eksport `build_rag_context_for_modify`, `index_project_vector_store`. |

**Przepływ (jak w tutorialu):**

1. **Ładowanie** — pliki tekstowe z katalogu projektu (`.py`, `.html`, `.md`, `.txt`, `.yml`, `.toml`, `.json`, `.css`, `.js`), z pominięciem katalogów jak w `project_fs` (`images`, `__pycache__`, `.git`, itd.) i plików zbyt dużych.
2. **Dzielenie** — `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=200`, `add_start_index=True`), jak w sekcji *Splitting documents* w tutorialu.
3. **Embedding + magazyn** — `OpenAIEmbeddings(model="text-embedding-3-small")` oraz `InMemoryVectorStore` z `langchain_core.vectorstores`, następnie `add_documents` (odpowiednik indeksowania z tutorialu).
4. **Retrieval** — `similarity_search(query, k=8)` na zapytaniu złożonym z: opcjonalnych wskazówek użytkownika, fragmentów Task / Arch / Tech.

**Pełne pliki dla kodera:** ze ścieżek w metadanych `source` zwróconych chunków oraz z listy krytycznych plików (`backend/main.py`, `backend/database.py`, `backend/agent.py`, `frontend/index.html`, `README.md` — jeśli istnieją) budowany jest blok `<project_files_full>`, żeby model nadal zwracał **kompletne** pliki przy edycji, a nie tylko fragmenty.

**Fallback:** przy braku `OPENAI_API_KEY` lub pustym indeksie używany jest poprzedni model: pełna treść wszystkich plików z `existing_project_files` (bez embeddingów).

### 1.2 Stan grafu

W [agents/state.py](agents/state.py) dodano pole:

- `user_project_guidance: str` — tekst wpisany przy starcie `main.py` (może być pusty).

### 1.3 Prompt coder (tryb CREATE)

`build_coder_prompt_create` przyjmuje opcjonalne `user_guidance` — te same wskazówki z `main.py` są doklejane przy generowaniu projektu od zera.

### 1.4 Prompt coder (tryb MODIFY)

[agents/prompts/coder.py](agents/prompts/coder.py) — `build_coder_prompt_modify` przyjmuje:

- `rag_retrieval_block` — sformatowany wynik `similarity_search` (z adnotacją *data only* / ochrona przed traktowaniem kodu jako instrukcji, w duchu sekcji *Security: indirect prompt injection* z tutorialu),
- `full_files_block` — pełne pliki w znaczniku `<project_files_full>`,
- `user_guidance` — priorytetowe wskazówki użytkownika.

Usunięto sztywną listę wymagań „TECHNICAL REQUIREMENTS FOR AUTH” z domyślnego promptu — zmiany wynikają z Task/Arch/Tech i z wskazówek użytkownika.

### 1.5 `main.py`

- Po wyborze fazy zawsze można wpisać **opcjonalne wskazówki** (jedna linia); trafiają do `user_project_guidance` i do zapytania RAG oraz prompu `coder_agent`.
- Tekst przy **human_review** doprecyzowuje, że można wpisać **konkretne uwagi** do szkicu (oprócz `ok` / `akceptuj`).

### 1.6 Zależności

W [requirements.txt](requirements.txt) dodano: `langchain-text-splitters`.

---

## 2. Jak to działa (krok po kroku)

1. Uruchomienie: `python main.py` z katalogu `Pipeline-Agents`.
2. Wybór katalogu projektu i agentów jak wcześniej.
3. Opcjonalne wskazówki — wpisane zdania są zapisane w stanie grafu.
4. W fazie **code** w trybie **modify** węzeł `coder_agent_node`:
   - składa `rag_query` z `user_project_guidance` + skróconych Task/Arch/Tech;
   - wywołuje `build_rag_context_for_modify(output_dir, rag_query, existing_files)`;
   - buduje prompt z retrieval + pełnymi plikami;
   - jeśli RAG nie działa, używa wyłącznie pełnego zestawu plików z pamięci `load_project`.

5. Podczas przerywania na **human_review** nadal działa **feedback** z ostatniej wiadomości użytkownika (dopisek `FEEDBACK_SUFFIX` w prompcie), gdy nie jest to sama akceptacja.

---

## 3. Wymagania środowiskowe

- **`OPENAI_API_KEY`** — wymagany do embeddingów i do normalnego działania LLM; bez niego RAG się nie indeksuje i używany jest fallback pełnoplikowy.
- Koszt: embeddingi przy każdym uruchomieniu fazy **code** w trybie modify (indeks w pamięci, bez trwałego vector store — najprostszy wariant jak w tutorialu z `InMemoryVectorStore`).

---

## 4. Gdzie szukać w kodzie

| Temat | Lokalizacja |
|-------|-------------|
| Indeks + search | `agents/rag/project_rag.py` |
| Podłączenie w agencie kodu | `agents/nodes.py` → `coder_agent_node` |
| Treść promptu MODIFY | `agents/prompts/coder.py` |
| Pole stanu | `agents/state.py` |
| Wejście użytkownika przy starcie | `main.py` |
| Lista wykluczeń katalogów (spójność z load projektu) | `agents/helpers/project_fs.py` (`EXCLUDE_DIRS`) |

---

## 5. Dalsze możliwe usprawnienia (poza zakresem tej iteracji)

- Trwały cache indeksu na dysku (uniknięcie ponownego embeddingu przy każdym runie).
- Osobny węzeł „planista” z listą plików do edycji.
- Rozszerzenie RAG o narzędzie `retrieve_context` w pętli agenta (wariant *RAG agents* z tutorialu).
