# Prompt Perfector - Developer Notes

## Project Structure

- `promptperfector/` - Main package
  - `main.py` - Entry point
  - `ui/` - UI components (PySide6)
    - `project_screen.py` - Project selection/creation UI
    - `flowchart_widget.py` - Flowchart editing UI (nodes, LLM modification)
    - `final_prompt_widget.py` - Final prompt display
    - `main_window.py` - Main window and navigation
  - `logic/` - Business logic
    - `db.py` - SQLite database logic (projects, flowchart versions)
    - `flowchart.py` - Flowchart model
    - `llm.py` - LLM stub logic
- `requirements.txt` - Python dependencies
- `setup.py` - Build and install script
- `ship/`, `debug/` - Build output folders

## Build & Run

- Install dependencies: `pip install -r requirements.txt`
- Initialize database: `python -m promptperfector.logic`
- Run in debug: `python -m promptperfector.main`
- Build executable (debug): `python -m PyInstaller --onefile --distpath debug promptperfector/main.py`
- Build executable (ship): `python -m PyInstaller --onefile --distpath ship --noconsole promptperfector/main.py`

## Features
- Project management: create/select projects, each with unique ID
- Flowchart versioning: each LLM modification or manual save creates a new version
- Flowchart editing: add/edit nodes, connectors (UI basic), LLM modification textbox
- All flowchart versions stored in SQLite DB, linked to project
- Final prompt generated from latest flowchart version
- LLM integration is stubbed; replace in `logic/llm.py` for real LLM

## Notes
- UI is basic; extend for full flowchart editing and connector logic as needed
- Database file: `promptperfector.db` in project root
- Replace LLM logic in `logic/llm.py` with actual local LLM integration
