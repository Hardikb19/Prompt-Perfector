
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QHBoxLayout, QMenuBar, QMenu, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal

from .flowchart_canvas import FlowchartCanvas
from ..logic.flowchart import FlowchartModel
from ..logic import db
from promptperfector.logic.logger import log_info, log_debug

import functools
from ..logic import db

class FlowchartWidget(QWidget):
    goto_final_prompt = Signal()
    switch_project = Signal()
    new_project = Signal()

    def __init__(self, model, project_id, parent=None):
        log_info(f"Opening project: {project_id}")
        super().__init__(parent)
        self.model = model
        self.project_id = project_id
        self.layout = QVBoxLayout(self)

        # File menu
        self.menu_bar = QMenuBar(self)
        file_menu = QMenu("File", self.menu_bar)
        switch_action = QAction("Switch Project", self)
        new_action = QAction("New Project", self)
        file_menu.addAction(switch_action)
        file_menu.addAction(new_action)
        self.menu_bar.addMenu(file_menu)
        self.layout.setMenuBar(self.menu_bar)
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
        self.layout.addLayout(version_layout)
        self.refresh_versions()

        # Canvas area (infinite, for flowchart)
        self.canvas = FlowchartCanvas()
        self.layout.addWidget(self.canvas, stretch=5)
        # Load latest version from DB if available, else use provided model
        latest = db.get_latest_flowchart(self.project_id)
        if latest:
            log_info(f"Loaded latest flowchart from DB for project {self.project_id} on first render.")
            self.canvas.import_from_model(latest)
        else:
            log_info(f"No flowchart found in DB for project {self.project_id}, using provided model.")
            self.canvas.import_from_model(self.model.to_json())

        # Connect autosave hooks
        self.canvas.on_update = self.autosave

        # Generate Button (top right)
        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.goto_final_prompt.emit)
        btn_layout.addStretch()
        btn_layout.addWidget(self.generate_btn)
        self.layout.addLayout(btn_layout)

        # LLM modification box (bottom)
        self.llm_edit = QTextEdit()
        self.llm_edit.setPlaceholderText("Text box to modify flow chart from using LLM")
        self.layout.addWidget(self.llm_edit, stretch=1)
        self.llm_btn = QPushButton("Modify with LLM")
        self.llm_btn.clicked.connect(self.modify_with_llm)
        self.layout.addWidget(self.llm_btn)

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
