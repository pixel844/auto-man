import sys
import platform
import subprocess
from loguru import logger

def get_cpu_info() -> str:
    try:
        if sys.platform == "win32":
            res = subprocess.run(["wmic", "cpu", "get", "name"], capture_output=True, text=True)
            return res.stdout.split("\n")[1].strip() if len(res.stdout.split("\n")) > 1 else ""
    except: pass
    return platform.processor()

def is_snapdragon() -> bool:
    cpu = get_cpu_info().lower()
    found = any(kw in cpu for kw in ["snapdragon", "x elite", "x plus", "qualcomm"])
    if found: logger.info(f"Hardware: {cpu} (NPU Supported)")
    return found

def run_all_checks():
    cpu = get_cpu_info()
    npu = is_snapdragon()
    return {"npu": npu, "cpu": cpu}
