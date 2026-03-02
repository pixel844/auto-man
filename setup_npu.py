import os
import shutil
import re
import platform
from pathlib import Path

def get_platform_info():
    system = platform.system().lower() # 'windows', 'linux'
    machine = platform.machine().lower() # 'amd64', 'arm64', 'aarch64'
    
    if system == "windows":
        if "arm" in machine or "aarch" in machine:
            arch_dirs = ["arm64x-windows-msvc", "aarch64-windows-msvc"]
        else:
            arch_dirs = ["x86_64-windows-msvc"]
        ext = ".dll"
        skel_ext = ".so"
    else: # Linux
        if "arm" in machine or "aarch" in machine:
            arch_dirs = ["aarch64-linux-clang"]
        else:
            arch_dirs = ["x86_64-linux-clang"]
        ext = ".so"
        skel_ext = ".so"
        
    return system, arch_dirs, ext, skel_ext

def ensure_npu_env(lib_dir: Path):
    system, arch_dirs, ext, skel_ext = get_platform_info()
    
    if is_env_ready(lib_dir, ext):
        print(f"NPU environment is already set up in {lib_dir}")
        return True

    print(f"NPU environment incomplete for {system}. Searching for QAIRT...")
    
    qairt_root, qairt_lib_path = find_qairt(arch_dirs)
    if not qairt_root:
        print("QAIRT SDK not found in standard paths. Skipping automated extraction.")
        return False
        
    print(f"Found QAIRT at: {qairt_root}")
    os.makedirs(lib_dir, exist_ok=True)

    # 1. Copy Runtime Binaries
    runtime_patterns = [f"QnnHtp{ext}", f"QnnSystem{ext}", f"QnnCpu{ext}", f"QnnHtpV73Stub{ext}", f"QnnHtpV81Stub{ext}"]
    for pattern in runtime_patterns:
        src = qairt_lib_path / pattern
        if src.exists():
            shutil.copy2(src, lib_dir / pattern)
            print(f"Extracted: {pattern}")

    # 2. Copy Skel/Firmware (Hexagon specific)
    skel_file = f"libQnnHtpV73Skel{skel_ext}"
    skel_found = False
    # Search in common hexagon lib paths inside QAIRT
    hexagon_roots = [qairt_root / "lib" / "hexagon-v73", qairt_root / "lib" / "hexagon-v81"]
    
    for h_root in hexagon_roots:
        for subdir in ["unsigned", "signed", ""]:
            src = h_root / subdir / skel_file
            if src.exists():
                shutil.copy2(src, lib_dir / skel_file)
                print(f"Extracted: {skel_file} (from {h_root.name}/{subdir})")
                skel_found = True
                break
        if skel_found: break

    return True

def is_env_ready(lib_dir: Path, ext: str):
    if not lib_dir.exists(): return False
    # Basic check for the primary HTP stub
    return (lib_dir / f"QnnHtp{ext}").exists()

def find_qairt(arch_dirs):
    search_roots = [
        r"C:\Qualcomm\AIStack\QAIRT",
        r"C:\Qualcomm\QAIRT",
        "/opt/qcom/qairt",
        str(Path.home() / "qualcomm" / "qairt")
    ]

    candidates = []
    for root_str in search_roots:
        root = Path(root_str)
        if not root.exists(): continue
        try:
            for entry in root.iterdir():
                if entry.is_dir() and (entry / "lib").exists():
                    candidates.append(entry)
        except OSError: continue

    if not candidates: return None, None

    # Sort by name (highest version usually)
    candidates.sort(reverse=True)
    best = candidates[0]
    
    for arch in arch_dirs:
        d = best / "lib" / arch
        if d.exists():
            return best, d

    return best, None
