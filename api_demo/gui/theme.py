"""
api_demo.gui.theme
~~~~~~~~~~~~~~~~~~

主题管理：亮色 / 暗色 / 跟随系统。

- Theme: 三个枚举值
- ThemeManager: 单例式管理器，应用主题到 ttk.Style + 已注册的 tk 控件

用法：

    from api_demo.gui.theme import ThemeManager, Theme

    mgr = ThemeManager(root)
    mgr.apply_preference(Theme.DARK)

    # 自定义非 ttk 控件注册进来（tk.Text / tk.Listbox 等）
    my_text = tk.Text(parent)
    mgr.register(my_text)

    # 切主题时自动重绘
    mgr.toggle()  # light -> dark -> system -> light
"""
from __future__ import annotations

import platform
import tkinter as tk
from enum import Enum
from tkinter import ttk

from .constants import (
    METHOD_COLORS,
    PAD_LG,
    PAD_MD,
    PAD_SM,
    PALETTE_DARK,
    PALETTE_LIGHT,
)


class Theme(Enum):
    """主题枚举。"""

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# 循环顺序：工具栏按钮单击循环用
THEME_CYCLE = [Theme.LIGHT, Theme.DARK, Theme.SYSTEM]

# 主题显示文案
THEME_LABELS = {
    Theme.LIGHT: "亮色",
    Theme.DARK: "暗色",
    Theme.SYSTEM: "跟随系统",
}


# ==================== 系统主题检测 ====================


def detect_system_theme() -> Theme:
    """
    查询操作系统的当前主题。

    - Windows: 读注册表 HKCU\\...\\Themes\\Personalize\\AppsUseLightTheme
    - macOS: defaults read -g AppleInterfaceStyle
    - 其他: 默认 LIGHT
    """
    try:
        if platform.system() == "Windows":
            return _detect_windows_theme()
        if platform.system() == "Darwin":
            return _detect_macos_theme()
    except Exception:
        pass
    return Theme.LIGHT


def _detect_windows_theme() -> Theme:
    """Windows 通过注册表查询应用主题。失败返回 LIGHT。"""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        # AppsUseLightTheme = 1 是亮色，0 是暗色
        return Theme.LIGHT if value == 1 else Theme.DARK
    except Exception:
        return Theme.LIGHT


def _detect_macos_theme() -> Theme:
    """macOS 通过 defaults 命令查询。"""
    import subprocess

    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        # 命令失败（exit != 0）表示未设置 Dark = 亮色
        if result.returncode == 0 and "Dark" in result.stdout:
            return Theme.DARK
        return Theme.LIGHT
    except Exception:
        return Theme.LIGHT


# ==================== 主题管理器 ====================


class ThemeManager:
    """
    主题管理器。

    职责：
      1. 应用主题到 ttk.Style（configure 所有标准 widget）
      2. 维护一个非 ttk 控件的注册表（tk.Text 等），切主题时同步更新
      3. 提供 method_color(method) 接口给其他 widget 取方法色
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.preference: Theme = Theme.LIGHT    # 用户选择
        self.current: Theme = Theme.LIGHT       # 实际生效
        self._styles_applied: bool = False      # ttk 样式是否已应用过

        # 注册的非 ttk 控件列表（tk.Text / tk.Listbox 等需要手动改色）
        self._registered_widgets: list = []

        # 主题切换回调（用于刷新方法色等自定义 widget）
        self._listeners: list = []

    # ---------- 应用主题 ----------

    def apply_preference(self, pref: Theme) -> None:
        """应用用户偏好。SYSTEM 时查询系统设置。"""
        self.preference = pref
        actual = detect_system_theme() if pref == Theme.SYSTEM else pref
        self._switch(actual)

    def toggle(self) -> Theme:
        """循环切换主题：light → dark → system → light。返回切换后的实际主题。"""
        idx = THEME_CYCLE.index(self.preference)
        next_pref = THEME_CYCLE[(idx + 1) % len(THEME_CYCLE)]
        self.apply_preference(next_pref)
        return self.current

    def _switch(self, theme: Theme) -> None:
        """实际切换：更新 ttk.Style + 注册的 tk 控件 + 通知监听者。"""
        if theme == self.current and self._styles_applied:
            # 已经应用过同主题，避免重复 configure
            return
        self.current = theme
        palette = self.palette()
        self._apply_ttk_styles(palette)
        self._refresh_registered_widgets(palette)
        self._styles_applied = True
        self._notify_listeners()

    # ---------- 调色板 ----------

    def palette(self) -> dict:
        """返回当前主题的调色板字典。"""
        return PALETTE_LIGHT if self.current == Theme.LIGHT else PALETTE_DARK

    def method_color(self, method: str) -> str:
        """返回指定 HTTP 方法在当前主题下的颜色。"""
        key = "light" if self.current == Theme.LIGHT else "dark"
        return METHOD_COLORS.get(method.upper(), METHOD_COLORS["GET"]).get(key, "#888888")

    # ---------- ttk.Style 配置 ----------

    def _apply_ttk_styles(self, palette: dict) -> None:
        """配置 ttk.Style，让所有标准 widget 用上主题色。"""
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            return  # clam 不可用，保持默认主题

        bg = palette["bg"]
        surface = palette["surface"]
        surface_alt = palette["surface_alt"]
        border = palette["border"]
        border_strong = palette["border_strong"]
        text = palette["text"]
        text_muted = palette["text_muted"]
        primary = palette["primary"]
        primary_hover = palette["primary_hover"]
        primary_active = palette["primary_active"]
        primary_text = palette["primary_text"]

        # 基础样式
        style.configure(".", background=bg, foreground=text)
        style.configure("TFrame", background=bg)
        style.configure("Surface.TFrame", background=surface)
        style.configure("Alt.TFrame", background=surface_alt)
        style.configure("TLabel", background=bg, foreground=text)
        style.configure("Muted.TLabel", background=bg, foreground=text_muted)
        style.configure("Surface.TLabel", background=surface, foreground=text)
        style.configure("Muted.Surface.TLabel", background=surface, foreground=text_muted)

        # 按钮
        style.configure(
            "TButton",
            background=surface,
            foreground=text,
            bordercolor=border,
            lightcolor=surface,
            darkcolor=surface,
            focuscolor=primary,
            padding=(PAD_MD, PAD_SM),
        )
        style.map(
            "TButton",
            background=[("active", surface_alt), ("pressed", surface_alt), ("disabled", surface)],
            foreground=[("disabled", text_muted)],
        )

        # Primary 按钮（强调色，用于「发送」等主要操作）
        style.configure(
            "Primary.TButton",
            background=primary,
            foreground=primary_text,
            bordercolor=primary,
            lightcolor=primary,
            darkcolor=primary,
            focuscolor=primary,
            padding=(PAD_LG, PAD_SM),
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", primary_hover),
                ("pressed", primary_active),
                ("disabled", surface_alt),
            ],
            foreground=[("disabled", text_muted)],
        )

        # 输入框
        style.configure(
            "TEntry",
            fieldbackground=surface,
            foreground=text,
            bordercolor=border_strong,
            lightcolor=border_strong,
            darkcolor=border_strong,
            insertcolor=text,
        )
        style.configure(
            "TSpinbox",
            fieldbackground=surface,
            foreground=text,
            bordercolor=border_strong,
            arrowcolor=text_muted,
            insertcolor=text,
        )
        style.configure(
            "TCombobox",
            fieldbackground=surface,
            foreground=text,
            bordercolor=border_strong,
            arrowcolor=text_muted,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", surface)],
            foreground=[("readonly", text)],
        )

        # Notebook / 页签
        style.configure("TNotebook", background=bg, bordercolor=border)
        style.configure("TNotebook.Tab", background=surface_alt, padding=(PAD_MD, PAD_SM))
        style.map(
            "TNotebook.Tab",
            background=[("selected", bg), ("active", surface)],
            foreground=[("selected", text), ("!selected", text_muted)],
        )

        # Checkbutton
        style.configure("TCheckbutton", background=bg, foreground=text, focuscolor=primary)
        style.map("TCheckbutton", foreground=[("disabled", text_muted)])

        # 分隔条
        style.configure("TSeparator", background=border)

        # LabelFrame
        style.configure(
            "TLabelframe",
            background=bg,
            foreground=text_muted,
            bordercolor=border,
        )
        style.configure("TLabelframe.Label", background=bg, foreground=text_muted)

        # Scrollbar
        style.configure(
            "Vertical.TScrollbar",
            background=surface,
            bordercolor=border,
            arrowcolor=text_muted,
            troughcolor=surface_alt,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=surface,
            bordercolor=border,
            arrowcolor=text_muted,
            troughcolor=surface_alt,
        )

    # ---------- 注册的非 ttk 控件 ----------

    def register(self, widget) -> None:
        """注册一个非 ttk 控件，切主题时自动更新它的颜色。"""
        if widget not in self._registered_widgets:
            self._registered_widgets.append(widget)
        # 立即用当前 palette 应用一次
        self._apply_widget_colors(widget, self.palette())

    def _refresh_registered_widgets(self, palette: dict) -> None:
        """切主题时遍历所有注册的 widget 应用新色。"""
        alive = []
        for w in self._registered_widgets:
            try:
                if not w.winfo_exists():
                    continue
                self._apply_widget_colors(w, palette)
                alive.append(w)
            except tk.TclError:
                continue
        self._registered_widgets = alive

    def _apply_widget_colors(self, widget, palette: dict) -> None:
        """对单个非 ttk 控件（tk.Text / tk.Listbox 等）应用主题色。"""
        cls = widget.winfo_class()
        try:
            if cls == "Text":
                widget.configure(
                    background=palette["code_bg"],
                    foreground=palette["code_fg"],
                    insertbackground=palette["text"],
                    selectbackground=palette["primary"],
                    selectforeground=palette["primary_text"],
                )
            elif cls == "Listbox":
                widget.configure(
                    background=palette["surface"],
                    foreground=palette["text"],
                    selectbackground=palette["primary"],
                    selectforeground=palette["primary_text"],
                )
            elif cls == "Canvas":
                widget.configure(background=palette["bg"])
            elif cls == "Entry":  # tk.Entry（不是 ttk.Entry）
                widget.configure(
                    background=palette["surface"],
                    foreground=palette["text"],
                    insertbackground=palette["text"],
                )
            elif cls in ("Frame", "Toplevel"):
                widget.configure(background=palette["bg"])
            elif cls == "Label":
                widget.configure(
                    background=palette["bg"],
                    foreground=palette["text"],
                )
        except tk.TclError:
            # 控件已销毁，忽略
            pass

    # ---------- 监听器 ----------

    def add_listener(self, callback) -> None:
        """注册主题切换回调（用于刷新非颜色依赖的 UI，如方法染色）。"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def _notify_listeners(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                pass