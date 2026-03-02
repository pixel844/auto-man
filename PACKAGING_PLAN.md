# Application Packaging & Compilation Plan

## 1. Overview
The goal is to bundle Auto-Man into a single-file executable for Windows and Linux, and explore a mobile package for Android.

## 2. Desktop (Windows & Linux)
We will use **PyInstaller** or **Nuitka** for creating standalone binaries.

- **Tools:**
    - `pip install pyinstaller`
- **Execution Strategy:**
    - **Step 1: Resource Bundling:** Create a `.spec` file that includes:
        - `models/` folder (default models).
        - `mcp_server.py`, `llm_engine.py`, `rag.py`, `gui.py`, `setup_npu.py`.
        - PyQt6 binaries and plugins.
    - **Step 2: Dependency Mapping:** Ensure `llmware` and its C++ shared objects are correctly collected.
    - **Step 3: Compilation:**
        - **Windows:** `pyinstaller --onefile --windowed --add-data "models;models" main.py`
        - **Linux:** `pyinstaller --onefile --add-data "models:models" main.py`
- **Optimization:** Use **Nuitka** for better performance and obfuscation if required.

## 3. Android Support
To run Python on Android with a GUI, we have two primary paths:

- **Option A: Buildozer (Kivy/MD)**
    - **Pros:** Mature tool for converting Python projects to `.apk`.
    - **Cons:** Requires refactoring the PyQt6 UI to Kivy.
- **Option B: BeeWare (Briefcase)**
    - **Pros:** Uses native Android widgets.
    - **Cons:** Complex dependency management for heavy libraries like `onnxruntime`.
- **Option C: Termux (CLI only)**
    - **Pros:** Works today without modification.
    - **Recommendation:** Provide a one-line install script for Termux.

## 4. Automation
- [ ] Create a `build.py` script to automate the PyInstaller process.
- [ ] Set up GitHub Actions to build and release binaries for Windows (ARM64/x86) and Linux (aarch64/x86).
