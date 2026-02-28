# 🤖 Multi-Agent Software Builder (LangGraph Pipeline)

Ten projekt to w pełni zautomatyzowany, oparty na agentach system AI, który symuluje pracę całego zespołu IT. Zespół sztucznej inteligencji potrafi samodzielnie przeprowadzić proces tworzenia oprogramowania (SDLC) – od zebrania wymagań biznesowych, przez zaprojektowanie architektury i napisanie kodu, aż po konteneryzację i fizyczne uruchomienie aplikacji w Dockerze.

Projekt został zbudowany przy użyciu frameworka **LangGraph** oraz modeli **OpenAI (GPT-4o)** i jest zoptymalizowany pod kątem uruchamiania w **LangGraph Studio**.

---

## 🏗️ Architektura Systemu i Agenci

System opiera się na architekturze typu *Supervisor-Worker* ze współdzielonym stanem (`StateGraph`). 

1. 🧠 **Supervisor (Lead PM):** Orkiestrator, który analizuje aktualną fazę projektu i kieruje zadania do odpowiednich specjalistów.
2. 💼 **Task Agent (Business Analyst):** Definiuje wymagania biznesowe i zakres MVP (zapisywane do `task_definition.md`).
3. 📐 **Architecture Agent (System Architect):** Projektuje logiczną strukturę systemu bazując na wymaganiach (`architecture.md`).
4. ⚙️ **Tech Agent (Tech Evaluator):** Dobiera optymalny stos technologiczny (Tech Stack) dla projektu (`technologies.md`).
5. 💻 **Coder Agent (Software Engineer):** Pisze właściwy kod aplikacji (frontend/backend) i formatuje go w ścisłą strukturę JSON.
6. 🕵️ **Review Agent (Code Auditor):** Przeprowadza rygorystyczne Code Review, szukając błędów i odstępstw od architektury (`code_review.md`).
7. 🐳 **Docker Agent (DevOps):** Tworzy pliki konfiguracyjne `Dockerfile` oraz `docker-compose.yml`.

### 🛡️ Węzeł I/O & Human-in-the-Loop (HITL)
Modele AI nie mają bezpośredniego dostępu do dysku. W tym celu zaimplementowano techniczny węzeł `save_and_proceed_node`. Po każdym szkicu system wstrzymuje działanie (przerwanie na węźle `human_review`), czekając na autoryzację człowieka. 
Gdy użytkownik wpisze **"ok"**, skrypt Python:
1. Parsuje kod z użyciem bezpiecznych wyrażeń regularnych (Regex).
2. Buduje strukturę katalogów na dysku lokalnym.
3. Zapisuje fizyczne pliki `.py`, `.js`, `.html` itp.
4. W ostatniej fazie wykonuje komendę `docker-compose up -d --build`, automatycznie stawiając gotowe środowisko.

---

## 🚀 Wymagania wstępne (Prerequisites)

Zanim uruchomisz projekt, upewnij się, że masz zainstalowane:
* **Python 3.10+**
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Musi być włączony w tle podczas ostatniej fazy!)
* Klucz API od OpenAI

---

## 🛠️ Instalacja i konfiguracja

1. **Sklonuj repozytorium i przejdź do folderu z projektem:**
    ```bash
   git clone <link-do-repo>
   cd Pipeline-Agents


2. **Utwórz wirtualne środowisko i aktywuj je:**
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate

3. **Zainstaluj wymagane biblioteki:**
    ```bash
    pip install langchain-openai langgraph python-dotenv

4. **Konfiguracja zmiennych środowiskowych:**
    ```bash
    Utwórz plik .env w głównym katalogu projektu i wklej swój klucz API:
        OPENAI_API_KEY=sk-twoj-sekretny-klucz-api