from PySide6.QtCore import QThread, Signal, QObject

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QHBoxLayout, QMenuBar, QMenu, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

from .flowchart_canvas import FlowchartCanvas
from ..logic.flowchart import FlowchartModel
from ..logic import db
from promptperfector.logic.logger import log_info, log_debug

import functools
from PySide6.QtWidgets import QSplitter, QPlainTextEdit, QToolButton, QSizePolicy, QStyle
from PySide6.QtCore import Qt, QTimer

class FlowchartWidget(QWidget):
    class LLMWorker(QObject):
        finished = Signal(str, Exception)
        def __init__(self, llm_runner, prompt):
            super().__init__()
            self.llm_runner = llm_runner
            self.prompt = prompt
        def run(self):
            from promptperfector.logic.logger import log_debug
            try:
                log_debug(f"LLMWorker: Running prompt on model: {getattr(self.llm_runner, 'model_path', None)}")
                log_debug(f"LLMWorker: Prompt: {self.prompt!r}")
                output = self.llm_runner.prompt(self.prompt)
                self.finished.emit(output, None)
            except Exception as e:
                log_debug(f"LLMWorker: Exception: {e}")
                self.finished.emit('', e)
    goto_final_prompt = Signal()
    switch_project = Signal()
    new_project = Signal()

    def __init__(self, model, project_id, parent=None):
        log_info(f"Opening project: {project_id}")
        super().__init__(parent)
        self.model = model
        self.project_id = project_id

        # LLM runner state
        self.llm_runner = None
        self.current_model_path = None

        # Main horizontal splitter
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)
        main_vbox = QVBoxLayout(self)
        main_vbox.addWidget(self.splitter)
        self.setLayout(main_vbox)

        # --- Left pane: existing vertical stack ---
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(0, 0, 0, 0)

        # File menu
        self.menu_bar = QMenuBar(self.left_widget)
        file_menu = QMenu("File", self.menu_bar)
        switch_action = QAction("Switch Project", self)
        new_action = QAction("New Project", self)
        file_menu.addAction(switch_action)
        file_menu.addAction(new_action)
        self.menu_bar.addMenu(file_menu)
        self.left_layout.setMenuBar(self.menu_bar)
        switch_action.triggered.connect(self.switch_project.emit)
        new_action.triggered.connect(self.new_project.emit)

        # Version and Model dropdowns (top right)
        version_layout = QHBoxLayout()
        version_layout.addStretch()
        self.model_dropdown = QComboBox()
        self.model_dropdown.setMinimumWidth(160)
        self.model_dropdown.setToolTip("Select LLM model (from models/ folder)")
        self.model_dropdown.currentIndexChanged.connect(self.on_model_changed)
        version_layout.addWidget(QLabel("Model:"))
        version_layout.addWidget(self.model_dropdown)
        self.version_dropdown = QComboBox()
        self.version_dropdown.setMinimumWidth(120)
        self.version_dropdown.currentIndexChanged.connect(self.on_version_changed)
        version_layout.addWidget(QLabel("Version:"))
        version_layout.addWidget(self.version_dropdown)
        self.left_layout.addLayout(version_layout)
        self.refresh_models()
        self.refresh_versions()

        # Canvas area (infinite, for flowchart)
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        # Toggle JSON button ("<>")
        self.toggle_json_btn = QToolButton()
        self.toggle_json_btn.setText("<>")
        self.toggle_json_btn.setToolTip("Show/Hide JSON Output")
        self.toggle_json_btn.setCheckable(True)
        self.toggle_json_btn.setChecked(False)
        self.toggle_json_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.toggle_json_btn.clicked.connect(self.toggle_json_box)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.toggle_json_btn)
        canvas_layout.addLayout(btn_row)
        self.canvas = FlowchartCanvas()
        canvas_layout.addWidget(self.canvas, stretch=5)
        self.left_layout.addWidget(canvas_container)

        
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        # Generate Button (top right)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.generate_btn)
        self.left_layout.addLayout(btn_layout)

        # LLM modification box (bottom)
        self.llm_edit = QTextEdit()
        self.llm_edit.setPlaceholderText("Text box to modify flow chart from using LLM")
        self.left_layout.addWidget(self.llm_edit, stretch=1)
        self.llm_btn = QPushButton("Modify with LLM")
        self.llm_btn.clicked.connect(self.modify_with_llm)
        self.left_layout.addWidget(self.llm_btn)

        self.splitter.addWidget(self.left_widget)

        # --- Right pane: JSON output box (initially hidden) ---
        self.json_widget = QWidget()
        self.json_layout = QVBoxLayout(self.json_widget)
        self.json_layout.setContentsMargins(0, 0, 0, 0)
        label_row = QHBoxLayout()
        label = QLabel("Current Flowchart JSON")
        label_row.addWidget(label)
        label_row.addStretch()
        self.json_layout.addLayout(label_row)
        self.json_box = QPlainTextEdit()
        self.json_box.setReadOnly(True)
        self.json_box.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.json_box.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 11pt;")
        self.json_layout.addWidget(self.json_box, stretch=1)
        # Hover-activated copy button
        self.copy_btn = QToolButton(self.json_box)
        self.copy_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.copy_btn.setToolTip("Copy JSON to clipboard")
        self.copy_btn.setStyleSheet("QToolButton { background: #eee; border: 1px solid #ccc; border-radius: 4px; padding: 2px; }")
        self.copy_btn.setVisible(False)
        self.copy_btn.clicked.connect(self.copy_json_to_clipboard)
        self.json_box.viewport().installEventFilter(self)
        self.json_box.viewport().setMouseTracking(True)
        self.json_box.viewport().mouseMoveEvent = self._json_mouse_move_event
        self.json_box.viewport().leaveEvent = self._json_leave_event
        self.splitter.addWidget(self.json_widget)
        self.json_widget.setVisible(False)
        self.splitter.setSizes([1, 0])

        # Load latest version from DB if available, else use provided model
        latest = db.get_latest_flowchart(self.project_id)
        if latest:
            log_info(f"Loaded latest flowchart from DB for project {self.project_id} on first render.")
            self.canvas.import_from_model(latest)
        else:
            log_info(f"No flowchart found in DB for project {self.project_id}, using provided model.")
            self.canvas.import_from_model(self.model.to_json())

        # Connect autosave hooks
        self.canvas.on_update = self._on_flowchart_update
        self._on_flowchart_update()

    def refresh_models(self):
        """Scan models/ for subfolders with .gguf files and populate the model dropdown."""
        import os
        from promptperfector.logic.llm.model_utils import list_available_models
        exe_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(exe_dir, '../..'))
        models_dir = os.path.join(root_dir, 'models')
        models = list_available_models(models_dir)
        self.model_dropdown.blockSignals(True)
        self.model_dropdown.clear()
        for name, path in models:
            self.model_dropdown.addItem(name, path)
        self.model_dropdown.blockSignals(False)
        if models:
            self.model_dropdown.setCurrentIndex(0)
        else:
            self.model_dropdown.addItem("No models found", None)


    def on_model_changed(self, idx):
        model_path = self.model_dropdown.itemData(idx)
        if not model_path or model_path == self.current_model_path:
            return
        # Stop previous runner if any
        if self.llm_runner:
            try:
                self.llm_runner.stop()
            except Exception as e:
                log_info(f"Error stopping previous LLM runner: {e}")
        # Start new runner
        try:
            from promptperfector.logic.llm.llm_runner import LlamaCppRunner
            self.llm_runner = LlamaCppRunner(model_path)
            self.llm_runner.start()
            self.current_model_path = model_path
            log_info(f"Started LLM runner for model: {model_path}")
        except Exception as e:
            self.llm_runner = None
            self.current_model_path = None
            log_info(f"Failed to start LLM runner: {e}")

    def on_generate_clicked(self):
        # Run a test prompt with the selected model and show output (async)
        idx = self.model_dropdown.currentIndex()
        model_path = self.model_dropdown.itemData(idx)
        log_debug(f"on_generate_clicked: model_path={model_path}")
        if not model_path or model_path == "No models found":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Model", "Please select a valid model from the dropdown.")
            return
        if not self.llm_runner or self.current_model_path != model_path:
            self.on_model_changed(idx)
        if not self.llm_runner:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "LLM Error", "Failed to load the selected model.")
            return
        prompt = "Say hello from " + self.model_dropdown.currentText() + " in spanish!"
        log_debug(f"on_generate_clicked: Sending prompt to LLM: {prompt!r}")

        # Start worker thread
        self.llm_thread = QThread()
        self.llm_worker = self.LLMWorker(self.llm_runner, prompt)
        self.llm_worker.moveToThread(self.llm_thread)
        self.llm_thread.started.connect(self.llm_worker.run)
        self.llm_worker.finished.connect(self.on_llm_finished)
        self.llm_worker.finished.connect(self.llm_thread.quit)
        self.llm_worker.finished.connect(self.llm_worker.deleteLater)
        self.llm_thread.finished.connect(self.llm_thread.deleteLater)
        self.generate_btn.setEnabled(False)
        self.llm_thread.start()

    def on_llm_finished(self, output, error):
        self.generate_btn.setEnabled(True)
        from PySide6.QtWidgets import QMessageBox
        if error:
            QMessageBox.critical(self, "LLM Error", f"Error running model: {error}")
        else:
            QMessageBox.information(self, "LLM Output", output.strip())

    def toggle_json_box(self):
        show = self.toggle_json_btn.isChecked()
        self.json_widget.setVisible(show)
        if show:
            self.splitter.setSizes([2, 1])
        else:
            self.splitter.setSizes([1, 0])

    def _on_flowchart_update(self):
        import json
        pretty = json.dumps(self.get_flow_json(), indent=2, ensure_ascii=False)
        self.json_box.setPlainText(pretty)
        self.autosave()

    def _json_mouse_move_event(self, event):
        # Show copy button on hover (top right corner)
        self.copy_btn.move(self.json_box.viewport().width() - self.copy_btn.width() - 8, 8)
        self.copy_btn.setVisible(True)
        QPlainTextEdit.mouseMoveEvent(self.json_box.viewport(), event)

    def _json_leave_event(self, event):
        self.copy_btn.setVisible(False)
        QPlainTextEdit.leaveEvent(self.json_box.viewport(), event)

    def copy_json_to_clipboard(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.json_box.toPlainText())

    def autosave(self):
        log_info(f"Autosave triggered for project: {self.project_id}")
        db.save_flowchart_version(self.project_id, self.get_flow_json())
        self.refresh_versions()

    def refresh_versions(self):
        log_debug(f"Refreshing version list for project: {self.project_id}")
        versions = db.list_flowchart_versions(self.project_id)
        self.version_dropdown.blockSignals(True)
        self.version_dropdown.clear()
        # Show only the latest 10 versions
        for v, created in versions[:10]:
            self.version_dropdown.addItem(f"v{v} ({created[:19]})", v)
        self.version_dropdown.blockSignals(False)
        if versions:
            self.version_dropdown.setCurrentIndex(0)

    def on_version_changed(self, idx):
        log_info(f"User selected version index: {idx} for project: {self.project_id}")
        if idx < 0:
            return
        v = self.version_dropdown.itemData(idx)
        if v is None:
            return
        # Load version from DB
        with db.get_connection() as conn:
            row = conn.execute('SELECT flowchart_json FROM flowcharts WHERE project_id=? AND version=?', (self.project_id, v)).fetchone()
            if row:
                import json
                log_info(f"Loading version {v} for project {self.project_id}")
                self.canvas.import_from_model(json.loads(row[0]))
        # Always update JSON output after version change
        self._on_flowchart_update()

    def get_flow_json(self):
        # Export from canvas to model/JSON
        return self.canvas.export_to_model()

    def modify_with_llm(self):
        log_info(f"User requested LLM modification for project: {self.project_id}")
        # Stub: Replace with actual LLM call
        user_query = self.llm_edit.toPlainText().strip()
        if not user_query:
            return
        # Simulate LLM modification: just add a node visually
        self.canvas.mouseDoubleClickEventFake(user_query)
        db.save_flowchart_version(self.project_id, self.get_flow_json())
