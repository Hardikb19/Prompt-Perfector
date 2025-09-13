from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QLineEdit, QLabel, QMessageBox
from ..logic import db

class ProjectScreen(QWidget):
    def __init__(self, on_project_selected):
        super().__init__()
        self.on_project_selected = on_project_selected
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Select or Create a Project")
        self.layout.addWidget(self.label)
        self.project_list = QListWidget()
        self.layout.addWidget(self.project_list)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("New project name")
        self.layout.addWidget(self.name_input)
        self.create_btn = QPushButton("Create Project")
        self.create_btn.clicked.connect(self.create_project)
        self.layout.addWidget(self.create_btn)
        self.project_list.itemDoubleClicked.connect(self.select_project)
        self.refresh_projects()

    def refresh_projects(self):
        self.project_list.clear()
        for pid, name in db.list_projects():
            self.project_list.addItem(f"{name} ({pid})")

    def create_project(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Project name cannot be empty.")
            return
        pid = db.create_project(name)
        self.refresh_projects()
        self.name_input.clear()

    def select_project(self, item):
        text = item.text()
        pid = text.split('(')[-1][:-1]
        self.on_project_selected(pid)
