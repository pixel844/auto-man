import sys
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QPushButton, QTextEdit, 
                             QProgressBar, QLabel, QMessageBox)
from cli import run_workflow

class GuiWorker(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(str)
    
    def __init__(self, repo):
        super().__init__()
        self.repo = repo
        
    def run(self):
        from llm_engine import LlmEngine
        from rag import Rag
        model, rag = LlmEngine(), Rag()
        try:
            rag.index_repo(self.repo)
            context = rag.get_context()
            
            # Embed concise task
            prompt = (
                "Task: Generate an extremely concise ROFF .man page.\n"
                "1. NAME: Short one-sentence summary.\n"
                "2. OPTIONS: List command line arguments.\n"
                "Be extremely brief.\n\n"
                f"CONTEXT:\n{context}"
            )
            
            content = []
            def cb(t): self.output.emit(t); content.append(t)
            model.generate(prompt, cb)
            
            p = Path.cwd() / "gui_output.man"
            from manual_generation import clean_roff_content
            p.write_text(clean_roff_content("".join(content)), encoding="utf-8")
            self.finished.emit(str(p))
        finally:
            model.cleanup()
            rag.cleanup()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto-Man (NPU)")
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText("Repo URL/Path")
        self.btn = QPushButton("Generate Simplified Manual")
        self.view = QTextEdit(); self.view.setReadOnly(True)
        
        layout.addWidget(self.input); layout.addWidget(self.btn); layout.addWidget(self.view)
        
        central = QWidget(); central.setLayout(layout)
        self.setCentralWidget(central)
        
        self.btn.clicked.connect(self.start)
        
    def start(self):
        self.view.clear()
        self.worker = GuiWorker(self.input.text())
        self.worker.output.connect(lambda t: self.view.insertPlainText(t))
        self.worker.finished.connect(lambda p: QMessageBox.information(self, "Done", f"Saved to {p}"))
        self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show(); sys.exit(app.exec())
