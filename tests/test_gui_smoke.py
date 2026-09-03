"""
GUI 冒烟测试
~~~~~~~~~~~

只验证两件事：
  1. api_demo.gui 模块可以正常导入
  2. 纯函数 `format_json` 行为正确（中文不转义、不可序列化对象不崩）

不做真正的 GUI 端到端测试（无头 CI 上运行不可靠，且本项目目标是演示工具）。
"""
from __future__ import annotations

import pytest


def test_gui_module_imports():
    """GUI 子包可以导入；tkinter 缺失时跳过。"""
    pytest.importorskip("tkinter", reason="当前环境没有 tkinter")
    from api_demo.gui.app import App, main  # noqa: F401

    assert callable(main), "main 必须是可调用对象"


def test_gui_init_exports():
    """gui/__init__.py 导出 App / main / format_json。"""
    pytest.importorskip("tkinter")
    from api_demo.gui import App, format_json, main

    assert callable(main)
    assert callable(format_json)
    assert App is not None


def test_format_json_chinese_not_escaped():
    """中文应原样输出（不被 \\uXXXX 转义）。"""
    pytest.importorskip("tkinter")
    from api_demo.gui.app import format_json

    out = format_json({"name": "张三", "city": "北京"})
    assert "张三" in out
    assert "北京" in out
    assert "\\u" not in out  # ensure_ascii=False 生效


def test_format_json_indents():
    """JSON 应有缩进（pretty print）。"""
    pytest.importorskip("tkinter")
    from api_demo.gui.app import format_json

    out = format_json({"a": 1, "b": 2})
    # 缩进 2 空格
    assert "\n  " in out


def test_format_json_unserializable_falls_back():
    """遇到不可序列化对象时返回非空字符串（不抛异常）。"""
    pytest.importorskip("tkinter")
    from api_demo.gui.app import format_json

    out = format_json(object())
    assert isinstance(out, str)
    assert out != ""


def test_format_json_list_and_scalar():
    """支持 list 和标量。"""
    pytest.importorskip("tkinter")
    from api_demo.gui.app import format_json

    assert format_json([1, 2, 3]) == "[\n  1,\n  2,\n  3\n]"
    assert format_json("hello") == '"hello"'
    assert format_json(None) == "null"