# 🤖 AI Internship Agents - Portfolio Projektów

Witaj w moim repozytorium! Znajdziesz tutaj projekty zrealizowane w ramach zadań stażowych AI. Repozytorium demonstruje praktyczne wykorzystanie sztucznej inteligencji, frameworka **LangGraph** oraz zaawansowanej architektury agentowej (Multi-Agent Systems) do automatyzacji procesów.

---

## 📂 Zawartość Repozytorium

To repozytorium to tzw. *monorepo*, które zawiera dwa niezależne projekty. Każdy z nich znajduje się w osobnym folderze i posiada własną, szczegółową dokumentację.

### 1. [Multi-Agent Software Builder (Pipeline Agents)](./Pipeline-Agents)
Zautomatyzowany system symulujący pracę całego zespołu IT (od analityka biznesowego po inżyniera DevOps). 
* **Technologie:** Python, LangGraph (StateGraph), OpenAI GPT-4o, Docker.
* **Kluczowe mechanizmy:** Architektura *Supervisor-Worker*, Human-in-the-Loop (akceptacja użytkownika przed przejściem do kolejnej fazy), parsowanie JSON za pomocą Regex oraz automatyczne budowanie środowiska w Dockerze.
* 📖 [Przejdź do dokumentacji projektu](./Pipeline-Agents/README.md)

### 2. [Recipe Agent (Asystent Kulinarny AI)](./Recipe-Agent-Full)
Inteligentny agent specjalizujący się w tematyce kulinarnej, potrafiący generować przepisy i analizować zdjęcia potraw.
* **Technologie:** Python, LangGraph, OpenAI (GPT-4o z funkcją Vision), Tool Calling.
* **Kluczowe mechanizmy:** Ścisłe instrukcje systemowe (Guardrails) blokujące tematy pozakulinarne, analiza obrazu (Base64) oraz automatyczne wywoływanie narzędzi (*Tool Calling*) w celu zapisu wygenerowanych przepisów do struktury `.json`.
* 📖 [Przejdź do dokumentacji projektu](./Recipe-Agent-Full/README.md)

---

## 🛠️ Globalny Stos Technologiczny
* **Język:** Python 3.11+
* **AI & LLM:** LangGraph, LangChain, OpenAI API
* **Infrastruktura:** Docker & Docker Compose
* **Środowisko:** LangGraph Studio, VS Code, Jupyter Notebook

---

## 🚀 Jak uruchomić projekty?
Każdy projekt wymaga osobnego skonfigurowania środowiska wirtualnego (`.venv`) oraz pliku `.env` z kluczami API. Szczegółowe instrukcje instalacji i uruchomienia znajdują się w plikach `README.md` wewnątrz odpowiednich folderów.

1. Wybierz projekt z listy powyżej.
2. Wejdź do jego folderu (np. `cd Pipeline-Agents`).
3. Postępuj zgodnie z instrukcjami z lokalnego pliku README.

---
*Projekty przygotowane w ramach stażu AI.*