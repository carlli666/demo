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


# ==================== 主题（Theme / ThemeManager）================


def test_theme_enum_three_values():
    """Theme 枚举有 light / dark / system 三种值。"""
    pytest.importorskip("tkinter")
    from api_demo.gui.theme import Theme

    assert Theme.LIGHT.value == "light"
    assert Theme.DARK.value == "dark"
    assert Theme.SYSTEM.value == "system"
    assert len(list(Theme)) == 3


def test_palettes_have_same_keys():
    """亮色和暗色调色板的键必须一致，否则 _refresh_registered_widgets 会炸。"""
    from api_demo.gui.constants import PALETTE_DARK, PALETTE_LIGHT

    assert set(PALETTE_LIGHT.keys()) == set(PALETTE_DARK.keys())


def test_method_colors_have_all_http_methods():
    """METHOD_COLORS 必须覆盖所有 HTTP_METHODS。"""
    from api_demo.gui.constants import HTTP_METHODS, METHOD_COLORS

    for m in HTTP_METHODS:
        assert m in METHOD_COLORS, f"{m} 不在 METHOD_COLORS 里"
        assert "light" in METHOD_COLORS[m]
        assert "dark" in METHOD_COLORS[m]


def test_theme_manager_can_be_constructed_and_switch():
    """ThemeManager 能实例化并切换主题。"""
    pytest.importorskip("tkinter")
    import tkinter as tk

    from api_demo.gui.theme import Theme, ThemeManager

    root = tk.Tk()
    root.withdraw()
    try:
        mgr = ThemeManager(root)
        # 默认亮色
        assert mgr.current == Theme.LIGHT
        assert mgr.palette()["bg"] == "#ffffff"

        # 切到暗色
        mgr.apply_preference(Theme.DARK)
        assert mgr.current == Theme.DARK
        assert mgr.palette()["bg"] == "#0f172a"

        # toggle 循环
        mgr.apply_preference(Theme.LIGHT)
        mgr.toggle()  # light -> dark
        assert mgr.current == Theme.DARK
        mgr.toggle()  # dark -> system
        assert mgr.preference == Theme.SYSTEM
        mgr.toggle()  # system -> light
        assert mgr.preference == Theme.LIGHT
    finally:
        root.destroy()


def test_theme_manager_method_color_changes_with_theme():
    """方法色随主题变化。"""
    pytest.importorskip("tkinter")
    import tkinter as tk

    from api_demo.gui.theme import Theme, ThemeManager

    root = tk.Tk()
    root.withdraw()
    try:
        mgr = ThemeManager(root)
        mgr.apply_preference(Theme.LIGHT)
        light_color = mgr.method_color("GET")
        mgr.apply_preference(Theme.DARK)
        dark_color = mgr.method_color("GET")
        # 亮暗色应不同（除非设计故意相同）
        assert light_color != dark_color
    finally:
        root.destroy()


def test_settings_dialog_includes_theme_field():
    """SettingsDialog 构造后应包含主题变量，并把 'dark' 映射到显示文案。"""
    pytest.importorskip("tkinter")
    import tkinter as tk

    from api_demo.gui.settings import SettingsDialog
    from api_demo.gui.theme import Theme

    root = tk.Tk()
    root.withdraw()
    try:
        dlg = SettingsDialog(root, {"theme": "dark"})
        assert hasattr(dlg, "var_theme")
        # 显示值是中文标签，内部存的是 Theme.value
        display_value = dlg.var_theme.get()
        # 反查映射得到内部 value
        internal = dlg._theme_display_to_value.get(display_value)
        assert internal == Theme.DARK.value
        # 默认主题映射也正确
        dlg2 = SettingsDialog(root, {"theme": "light"})
        internal2 = dlg2._theme_display_to_value.get(dlg2.var_theme.get())
        assert internal2 == Theme.LIGHT.value
        dlg.destroy()
        dlg2.destroy()
    finally:
        root.destroy()