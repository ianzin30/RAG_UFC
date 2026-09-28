"""Make FAISS and PyTorch share one OpenMP runtime in this virtualenv.

Run after uv sync on macOS. This repairs wheel linkage, not application code;
no KMP_DUPLICATE_LIB_OK workaround is enabled. Other platforms are untouched.
"""

import importlib.util
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != "darwin":
        return
    torch_root = Path(importlib.util.find_spec("torch").origin).parent
    faiss_root = Path(importlib.util.find_spec("faiss").origin).parent
    runtime = torch_root / "lib/libomp.dylib"
    for extension in faiss_root.glob("_swigfaiss*.so"):
        linkage = subprocess.check_output(["otool", "-L", str(extension)], text=True)
        original = "@loader_path/.dylibs/libomp.dylib"
        if original in linkage:
            subprocess.run(
                [
                    "install_name_tool",
                    "-change",
                    original,
                    str(runtime.resolve()),
                    str(extension),
                ],
                check=True,
            )
            subprocess.run(
                ["codesign", "--force", "--sign", "-", str(extension)], check=True
            )
            print(f"FAISS now shares PyTorch OpenMP: {extension}")


if __name__ == "__main__":
    main()
