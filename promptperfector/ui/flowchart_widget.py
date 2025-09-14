
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QHBoxLayout, QMenuBar, QMenu, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

from .flowchart_canvas import FlowchartCanvas
from ..logic.flowchart import FlowchartModel
from ..logic import db
from promptperfector.logic.logger import log_info, log_debug

import functools
from ..logic import db
from PySide6.QtWidgets import QSplitter, QPlainTextEdit, QToolButton, QSizePolicy, QStyle
from PySide6.QtCore import Qt, QTimer

class FlowchartWidget(QWidget):
    goto_final_prompt = Signal()
    switch_project = Signal()
    new_project = Signal()

    def __init__(self, model, project_id, parent=None):
        log_info(f"Opening project: {project_id}")
        super().__init__(parent)
        self.model = model
        self.project_id = project_id

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

        # Version dropdown (top right)
        version_layout = QHBoxLayout()
        version_layout.addStretch()
        self.version_dropdown = QComboBox()
        self.version_dropdown.setMinimumWidth(120)
        self.version_dropdown.currentIndexChanged.connect(self.on_version_changed)
        version_layout.addWidget(QLabel("Version:"))
        version_layout.addWidget(self.version_dropdown)
        self.left_layout.addLayout(version_layout)
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

        # Generate Button (top right)
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.goto_final_prompt.emit)
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
