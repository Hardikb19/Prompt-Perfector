
# Prompt Perfector - Developer Notes

## Project Structure

- `promptperfector/` - Main package
  - `main.py` - Application entry point, sets up QApplication and main window
  - `ui/` - UI components (PySide6)
    - `main_window.py` - Main window, navigation, and screen switching
    - `project_screen.py` - Project selection/creation UI, project list, new project dialog
    - `flowchart_widget.py` - Flowchart editing UI, version dropdown, LLM modification, JSON output pane
    - `flowchart_canvas.py` - Core canvas logic: node/connector classes, drag, edit, context menu, connector creation, autosave, import/export, dynamic sizing, subject/text fields, JSON sync
    - `final_prompt_widget.py` - Final prompt display, LLM output
  - `logic/` - Business logic
    - `db.py` - SQLite database logic (projects, flowchart versions, versioning, migrations)
    - `flowchart.py` - Flowchart model, node/connector data structures, serialization
    - `llm.py` - LLM stub logic (replaceable with real LLM integration)
- `requirements.txt` - Python dependencies
- `setup.py` - Build and install script
- `ship/`, `debug/` - Build output folders

## Build & Run

- Install dependencies: `pip install -r requirements.txt`
- Run: `python -m promptperfector.main`
- Build executable (debug): `python -m PyInstaller --onefile --distpath debug promptperfector/main.py`
- Build executable (ship): `python -m PyInstaller --onefile --distpath ship --noconsole promptperfector/main.py`

## Implementation Details

### UI Layer (PySide6)
- **Canvas:** Infinite, zoomable, QGraphicsView-based. Nodes are QGraphicsRectItem with QGraphicsTextItem for label. Connectors are custom ArrowLineItem with repeated arrowheads.
- **Node Interactions:**
  - Drag: QGraphicsItem.ItemIsMovable
  - Edit: Double-click or context menu opens dialog for subject/text
  - Connect: Click connector button, then another node to connect
  - Delete: Context menu for node/connector
  - Dynamic sizing: Node resizes to fit subject/text, connector buttons reposition
- **Connector Logic:**
  - Connectors store from_id/to_id, rerender on node move
  - Deletion updates both scene and internal connectors list
- **Version Dropdown:** QComboBox, shows latest 10 versions, triggers DB load and JSON/UI update
- **JSON Output Pane:** QPlainTextEdit, toggled with button, always reflects current flowchart state (autosync on any change or version switch)

### Autosave & Versioning
- **Autosave:** Triggers on meaningful events (node move, edit, connect, delete)
- **Versioning:**
  - Each autosave creates a new version in SQLite (project_id, version, timestamp, JSON blob)
  - Only latest 10 versions shown in dropdown for quick access
  - Switching versions updates both canvas and JSON output

### JSON Sync
- **Export:** `export_to_model` in canvas serializes all nodes/connectors, always includes both subject and text fields for each node
- **Import:** `import_from_model` loads subject/text with backward compatibility (if subject missing, uses text)
- **Live Update:** Any change (edit, connect, delete, version switch) triggers JSON output update and autosave

### LLM Integration
- **LLM Modify:** User enters instruction, flowchart JSON sent to LLM (stub), LLM returns modified JSON, new version created
- **Final Prompt:** Flowchart converted to text prompt using LLM, shown in final prompt screen
- **Stub:** Replace `logic/llm.py` for real LLM API

### Database (SQLite)
- **Tables:**
  - `projects` (id, name, created)
  - `flowcharts` (project_id, version, created, flowchart_json)
- **Versioning:** Each save creates new row in `flowcharts` with incremented version
- **Migrations:** Handled in `db.py` if schema changes

### Logging
- **File-based:** All major actions (node/connector create/delete, autosave, versioning, LLM calls) logged to `debug.log`
- **Debug/Ship Modes:** Debug mode logs everything, ship mode disables debug logs

### Extensibility
- **LLM:** Swap out `logic/llm.py` for any local LLM API
- **UI:** Add new node types, connector styles, or editing tools in `flowchart_canvas.py`
- **Persistence:** Add cloud sync or export/import by extending `db.py` and model logic

### Testing & Debugging
- **Debug Log:** Check `debug.log` for all UI/data actions
- **UI Testing:** Most UI logic in `flowchart_canvas.py` and `flowchart_widget.py`
- **Data Model:** Test import/export with both old and new JSON (subject/text)

### Known Issues & TODOs
- [ ] Node overlap prevention (planned)
- [ ] Undo/redo stack (planned)
- [ ] LLM backend integration (stub only)
- [ ] More robust error handling for DB/IO
