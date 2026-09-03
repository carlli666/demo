"""
run_gui.py
~~~~~~~~~~

GUI 桌面版启动脚本。

用法（在项目根目录执行）：

    python run_gui.py

说明：
  - tkinter 是 Python 自带的图形库，无需额外安装。
  - 如果没装包（pip install -e .），本脚本会把项目根目录加入 sys.path，
    这样可以直接 import api_demo。
"""
from __future__ import annotations

import os
import sys


def _ensure_path() -> None:
    """把项目根目录加入 sys.path，兜底支持「没装包直接 python run_gui.py」。"""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)


def main() -> None:
    """启动 GUI。"""
    _ensure_path()
    from api_demo.gui.app import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()