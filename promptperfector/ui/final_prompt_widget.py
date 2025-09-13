from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from ..logic.llm import LLM
from ..logic import db

class FinalPromptWidget(QWidget):
    def __init__(self, project_id=None, back_callback=None):
        super().__init__()
        self.project_id = project_id
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Final Prompt Screen")
        self.layout.addWidget(self.label)
        self.prompt_label = QLabel("")
        self.layout.addWidget(self.prompt_label)
        self.llm = LLM()
        self.back_callback = back_callback
        self.back_btn = QPushButton("Back to Flowchart")
        self.back_btn.clicked.connect(self.handle_back)
        self.layout.addWidget(self.back_btn)

    def handle_back(self):
        if self.back_callback:
            self.back_callback()

    def generate_prompt(self, flow_json=None):
        if self.project_id:
            flow_json = db.get_latest_flowchart(self.project_id)
        return self.llm.generate_prompt(flow_json)

    def set_prompt(self, prompt):
        self.prompt_label.setText(prompt)
