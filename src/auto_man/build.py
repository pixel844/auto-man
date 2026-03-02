import os
import subprocess
import sys
from pathlib import Path


def build_desktop():
    print("--- Starting Auto-Man Desktop Build ---")

    # Resolve paths
    base_dir = Path(__file__).parent.parent.parent
    venv_path = base_dir / ".venv"
    site_packages = venv_path / "Lib" / "site-packages"
    if not site_packages.exists():  # Linux fallback
        site_packages = (
            venv_path
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )

    llmware_lib = site_packages / "llmware" / "lib"

    # Construct PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",  # Hide console for GUI
        "--name",
        "auto-man",
        # Include llmware shared libs
        f"--add-data={llmware_lib}{os.pathsep}llmware/lib",
        # We don't bundle models by default to keep EXE size small and launch fast
        # The user should keep the 'models' folder next to the EXE
        "src/auto_man/main.py",
    ]


    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\n--- Build Successful! ---")
        print(f"Executable found in: {base_dir / 'dist'}")
    except subprocess.CalledProcessError as e:
        print(f"\n--- Build Failed! ---\n{e}")


if __name__ == "__main__":
    build_desktop()
