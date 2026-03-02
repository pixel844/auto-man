# Application Packaging Plan (Windows, Linux, Android)

## 1. Goal
Provide a streamlined method to compile `auto-man` into standalone executables for Windows and Linux, and outline a strategy for Android deployment.

## 2. Desktop Packaging (Windows & Linux)
We will use **PyInstaller** to bundle the Python interpreter, dependencies (including `llmware` and `onnxruntime`), and the application scripts into a single executable or directory.

### Prerequisites
- Python 3.10+
- `pip install pyinstaller`

### Build Command (Windows)
```powershell
pyinstaller --noconfirm --onedir --console --name "Auto-Man" ^
    --add-data "lib;lib" ^
    --add-data "models;models" ^
    --hidden-import="llmware" ^
    --hidden-import="onnxruntime_qnn" ^
    --hidden-import="PyQt6" ^
    main.py
```
*Note: We use `--onedir` instead of `--onefile` to make debugging QNN DLL loading easier.*

### Build Command (Linux)
```bash
pyinstaller --noconfirm --onedir --console --name "auto-man" 
    --add-data "lib:lib" 
    --add-data "models:models" 
    --hidden-import="llmware" 
    --hidden-import="onnxruntime_qnn" 
    main.py
```

### Post-Build Steps
1.  **QNN Binaries:** Ensure the `lib/` folder in the output directory contains the OS-specific QNN libraries (automatically handled if `setup_npu` ran correctly before build, but `add-data` ensures they are copied).
2.  **Models:** The `models/` folder is large. For a lighter installer, exclude `--add-data "models;models"` and let the app download models on the first run (using the existing fallback logic).

## 3. Android Packaging
Running this stack (PyQt6 + ONNX Runtime QNN + Python) natively on Android is complex. 

### Strategy A: Termux (Recommended)
This is not a "compiled app" but the most functional method for this specific tech stack.
1.  Install Termux.
2.  `pkg install python clang git`
3.  `pip install -r requirements.txt` (May require building wheels for numpy/grpc).
4.  Run `python main.py --repo ...`.

### Strategy B: Briefcase / Beeware
To build a true `.apk`, we must migrate the UI from PyQt6 to **Toga** (Beeware's native widget toolkit) or use a web-based UI wrapped in a WebView.
1.  `pip install briefcase`
2.  `briefcase new`
3.  Port `gui.py` to `app.py` using Toga widgets.
4.  `briefcase create android`
5.  `briefcase build android`
*Constraint:* ONNX Runtime QNN support on Android usually requires Java/Kotlin bindings or C++ NDK integration, not just the Python package. The Python `onnxruntime` package on Android is often CPU-only or NNAPI-based.

## 4. Next Actions
- [ ] Create a `build.spec` file for PyInstaller to automate the Windows/Linux build.
- [ ] Test the generated executable on a clean VM.
