import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Internal imports
from llm_engine import LlmEngine
from mcp_server import McpServer
from rag import Rag


class McpWorker(QObject):
    progress_update = pyqtSignal(str, int)
    token_received = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    tree_ready = pyqtSignal(str)

    def __init__(self, model_path, tokenizer_path):
        super().__init__()
        self.model_path = Path(model_path)
        self.tokenizer_path = Path(tokenizer_path)
        self.server = None
        self.repo_id = None

    def initialize_backend(self):
        try:
            self.progress_update.emit("Initializing NPU and Model...", 10)
            model = LlmEngine(self.model_path, self.tokenizer_path)
            rag = Rag(Path(__file__).parent)
            self.server = McpServer(model, rag)
            self.progress_update.emit("Backend Ready", 20)
        except Exception as e:
            self.error.emit(f"Initialization Error: {str(e)}")

    def get_tree(self, url):
        if not self.server:
            return
        try:
            response = self.server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "fetch_tree",
                    "params": {"url": url},
                }
            )
            if "error" in response:
                self.error.emit(response["error"]["message"])
            else:
                self.tree_ready.emit(response["result"]["content"][0]["text"])
        except Exception as e:
            self.error.emit(f"Tree Error: {str(e)}")

    def run_generation(self, url, repo_id=None):
        try:
            # 1. Add Repo
            self.progress_update.emit("Adding Repository...", 30)
            is_remote = url.startswith("http") or url.endswith(".git")
            resp = self.server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "add_repo",
                    "params": {"url": url, "is_remote": is_remote},
                }
            )
            self.repo_id = resp["result"]["content"][0]["text"].split(": ")[1]

            # 2. Index
            self.progress_update.emit("Indexing Repository (RAG)...", 50)
            self.server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "index_repo",
                    "params": {"id": self.repo_id},
                }
            )

            # 3. Generate
            self.progress_update.emit("Generating .man Page...", 70)

            repo_name = url.rstrip("/").split("/")[-1].replace(".git", "")
            output_filename = f"{repo_name}.man"
            output_path = Path.cwd() / output_filename

            output_content = []

            def token_cb(token):
                self.token_received.emit(token)
                output_content.append(token)

            summary_context = self.server.rag.retrieve_context(
                "General summary and purpose of the project"
            )
            commands_context = self.server.rag.retrieve_context(
                "Command line arguments, CLI flags, and main entry points"
            )

            full_context = f"Summary: {summary_context}\nCommands: {commands_context}"

            prompt = f"Generate a ROFF .man page for this repo:\n{full_context}"

            self.server.model.generate(prompt, token_cb)

            # Clean and save
            final_content = "".join(output_content)
            import re

            final_content = re.sub(r".\x08", "", final_content)
            final_content = final_content.replace("\x08", "").replace("\\b", "")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_content)

            self.progress_update.emit("Saving file...", 95)
            self.finished.emit(str(output_path))

        except Exception as e:
            self.error.emit(f"Generation Error: {str(e)}")
        finally:
            if hasattr(self.server, "rag"):
                self.server.rag.cleanup()


class TreeConfirmDialog(QDialog):
    def __init__(self, tree_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Repository Content")
        self.resize(500, 600)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Review the file structure before indexing:"))
        self.tree_view = QTextEdit()
        self.tree_view.setReadOnly(True)
        self.tree_view.setPlainText(tree_text)
        layout.addWidget(self.tree_view)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self, model_dir, repo_url=None):
        super().__init__()
        self.model_dir = Path(model_dir)
        self.repo_url = repo_url
        self.setWindowTitle("Auto-Man (NPU Accelerated)")
        self.resize(900, 700)
        self.setup_ui()
        self.setup_worker()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Header
        self.status_lbl = QLabel("Initializing...")
        layout.addWidget(self.status_lbl)

        # Input
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Repository Path or URL...")
        if self.repo_url:
            self.url_input.setText(self.repo_url)
        else:
            self.url_input.setText(str(Path(__file__).parent))
        input_layout.addWidget(self.url_input)

        self.gen_btn = QPushButton("Check Repo")
        self.gen_btn.clicked.connect(self.on_check_clicked)
        input_layout.addWidget(self.gen_btn)
        layout.addLayout(input_layout)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        # Output
        layout.addWidget(QLabel("Live Generation Output:"))
        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; font-family: Consolas;"
        )
        layout.addWidget(self.output_view)

    def setup_worker(self):
        self.thread = QThread()

        # Derive paths from model_dir
        model_path = (
            self.model_dir / "model.onnx" if self.model_dir.exists() else self.model_dir
        )
        tokenizer_path = (
            self.model_dir / "tokenizer.json"
            if self.model_dir.exists()
            else self.model_dir
        )

        self.worker = McpWorker(model_path, tokenizer_path)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.initialize_backend)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.token_received.connect(self.update_output)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.tree_ready.connect(self.show_confirm_dialog)

        self.thread.start()

    def update_progress(self, msg, val):
        self.status_lbl.setText(msg)
        self.progress.setValue(val)

    def update_output(self, token):
        self.output_view.insertPlainText(token)
        self.output_view.moveCursor(QTextCursor.MoveOperation.End)

    def on_check_clicked(self):
        url = self.url_input.text()
        if not url:
            return
        self.gen_btn.setEnabled(False)
        self.worker.get_tree(url)

    def show_confirm_dialog(self, tree_text):
        self.gen_btn.setEnabled(True)
        dlg = TreeConfirmDialog(tree_text, self)
        if dlg.exec():
            self.output_view.clear()
            self.worker.run_generation(self.url_input.text())

    def on_finished(self, path):
        self.update_progress("Generation Complete!", 100)
        QMessageBox.information(
            self, "Success", f"Manual generated successfully at:\n{path}"
        )

    def on_error(self, msg):
        self.gen_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Default for standalone testing
    window = MainWindow(model_dir=Path("models/qwen2.5-7b-instruct-onnx-qnn"))
    window.show()
    sys.exit(app.exec())
