# Cross-Platform Support Plan (Linux & Android)

## 1. Overview
The goal is to extend Auto-Man's NPU-accelerated capabilities to Linux (aarch64) and Android (via Termux or Native Python layers), leveraging LLMWare's support for Qualcomm QNN.

## 2. Linux (aarch64 / ARM64) Support
Linux support is natively possible on Snapdragon-based Linux systems (e.g., Lenovo ThinkPad X13s, specialized IoT boards).

- **Technical Requirements:**
    - **Host OS:** Ubuntu 22.04+ (aarch64).
    - **SDK:** Qualcomm AI Engine Direct (QNN) SDK for Linux.
    - **Drivers:** Latest Qualcomm NPU drivers for Linux.
- **Implementation Steps:**
    - [ ] **Library Path:** Ensure `.so` files from the QNN SDK are in `LD_LIBRARY_PATH`.
    - [ ] **Dependencies:** Build or fetch `llmware` and `onnxruntime-qnn` ARM64 wheels for Linux.
    - [ ] **Path Handling:** Update `main.py` and `mcp_server.py` to use `/tmp` or specific Linux paths instead of Windows-style temp folders.
    - [ ] **GUI:** Ensure PyQt6 is installed via `apt` or `pip` with X11/Wayland support.

## 3. Android Support
Direct Android support is "Indirect" via Python environments like Termux.

- **Technical Requirements:**
    - **App:** Termux (with X11 support if GUI is needed).
    - **SDK:** QNN SDK binaries for Android (shared libraries).
- **Implementation Steps:**
    - [ ] **Termux Setup:** Install `python`, `clang`, and `ninja` in Termux.
    - [ ] **QNN Loader:** Load the Android-specific QNN shared libraries (`.so`).
    - [ ] **Model Selection:** Ensure the models are compatible with the Android NPU delegate.
    - [ ] **Simplified UI:** Create a Kivy or reflex-based alternative UI if PyQt6 proves too heavy for mobile.

## 4. Universal Code Changes
- **Dynamic Library Loading:** 
    - Replace hardcoded `.dll` references with platform-aware logic:
      ```python
      suffix = ".dll" if os.name == "nt" else ".so"
      qnn_lib = f"libQnnHtp{suffix}"
      ```
- **Path Abstraction:** Use `pathlib` exclusively to handle `/` vs `` automatically.
- **Cloning Logic:** Ensure `git` is available in the system PATH on all platforms.
