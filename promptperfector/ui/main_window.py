
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QStackedWidget
from .project_screen import ProjectScreen
from .flowchart_widget import FlowchartWidget
from .final_prompt_widget import FinalPromptWidget
from ..logic import db, flowchart

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget, QInputDialog
from .project_screen import ProjectScreen
from .flowchart_widget import FlowchartWidget
from .final_prompt_widget import FinalPromptWidget
from ..logic import db, flowchart

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Prompt Perfector")
        self.resize(900, 700)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.stacked = QStackedWidget()
        self.project_screen = ProjectScreen(self.on_project_selected)
        self.flowchart_screen = None
        self.final_prompt_screen = None
        self.stacked.addWidget(self.project_screen)
        self.layout.addWidget(self.stacked)

        self.current_project_id = None

    def on_project_selected(self, project_id):
        self.current_project_id = project_id
        latest = db.get_latest_flowchart(project_id)
        if latest:
            model = flowchart.FlowchartModel.from_json(latest)
        else:
            model = flowchart.FlowchartModel()
        self.flowchart_screen = FlowchartWidget(model, project_id, self)
        self.final_prompt_screen = FinalPromptWidget(back_callback=self.back_to_flowchart)
        if self.stacked.count() > 1:
            self.stacked.removeWidget(self.stacked.widget(1))
        self.stacked.addWidget(self.flowchart_screen)
        self.stacked.setCurrentWidget(self.flowchart_screen)
        self.flowchart_screen.goto_final_prompt.connect(self.show_final_prompt)
        self.flowchart_screen.switch_project.connect(self.switch_project)
        self.flowchart_screen.new_project.connect(self.create_new_project)

    def show_final_prompt(self):
        flow_json = self.flowchart_screen.get_flow_json()
        prompt = self.final_prompt_screen.generate_prompt(flow_json)
        if self.stacked.count() > 2:
            self.stacked.removeWidget(self.stacked.widget(2))
        self.stacked.addWidget(self.final_prompt_screen)
        self.stacked.setCurrentWidget(self.final_prompt_screen)
        self.final_prompt_screen.set_prompt(prompt)

    def back_to_flowchart(self):
        self.stacked.setCurrentWidget(self.flowchart_screen)

    def switch_project(self):
        self.stacked.setCurrentWidget(self.project_screen)

    def create_new_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
        if ok and name.strip():
            pid = db.create_project(name.strip())
            self.project_screen.refresh_projects()
            self.on_project_selected(pid)
