"""
api_demo.gui
~~~~~~~~~~~~

基于 tkinter 的桌面 GUI 演示工具。

故意不通过 `api_demo/__init__.py` 导出本子包，以避免在无 GUI 环境下
（如服务器、CI）import 顶层 api_demo 时牵连 tkinter。

使用方式：

    from api_demo.gui import main
    main()

或者在命令行：

    hub
"""

from .app import App, format_json, main

__all__ = ["App", "main", "format_json"]