"""
api_demo.gui.settings
~~~~~~~~~~~~~~~~~~~~~

配置持久化（JSON 文件）+ 设置对话框（SettingsDialog）。

文件读写必须容错：配置文件损坏或缺失时不应阻止程序启动。
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

from .constants import CONFIG_PATH, CONFIG_PATH_LEGACY, DEFAULT_CONFIG, pick_ui_font
from .theme import THEME_LABELS, Theme


# ==================== 配置读写 ====================


def load_config() -> Dict[str, Any]:
    """
    从本地 JSON 文件读取配置。

    优先读新路径 ~/.intelligent-assistant-gui.json；
    不存在时依次尝试旧路径 ~/.hub-gui.json → ~/.api-demo-gui.json；
    都失败时返回默认值，绝不抛异常。

    :return: 配置字典
    """
    config = dict(DEFAULT_CONFIG)
    # CONFIG_PATH_LEGACY 是 list，CONFIG_PATH 单值 —— 包成 tuple 统一迭代
    paths = [CONFIG_PATH] + list(CONFIG_PATH_LEGACY)
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                config.update(data)
            break  # 读到一个就用，不再尝试
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
    return config


def save_config(config: Dict[str, Any]) -> None:
    """
    把配置写到本地 JSON 文件。

    - 默认不写 api_key（安全考虑）
    - 勾选 remember_key 后才写入 api_key
    - 写文件失败时静默忽略（不影响使用）

    :param config: 完整的配置字典
    """
    to_save = {k: v for k, v in config.items() if k != "api_key"}
    if config.get("remember_key"):
        to_save["api_key"] = config.get("api_key", "")
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except OSError:
        # 磁盘满 / 无权限 —— 演示工具不强制要求持久化
        pass


# ==================== 设置对话框 ====================


class SettingsDialog(tk.Toplevel):
    """
    模态设置对话框。

    调用方式：
        dlg = SettingsDialog(parent, current_config, on_save_callback)
        parent.wait_window(dlg)   # 等待对话框关闭

    :param parent: 父窗口（通常是主窗口的 root）
    :param current_config: 当前配置，用于初始化各字段
    :param on_save: 保存时回调，签名 `on_save(new_config: dict) -> None`
    """

    def __init__(
        self,
        parent: tk.Misc,
        current_config: Dict[str, Any],
        on_save: Optional[callable] = None,
        on_check_update: Optional[callable] = None,
    ):
        super().__init__(parent)
        self.on_save = on_save
        self.on_check_update = on_check_update or (lambda: None)

        self.title("设置")
        self.geometry("520x560")
        self.resizable(True, True)
        self.minsize(480, 480)
        self.transient(parent)  # 始终在父窗口之上

        # 默认值缓存（用户点取消时还原）
        self._initial = dict(current_config)

        # 控件变量
        self.var_api_key = tk.StringVar(value=current_config.get("api_key", ""))
        self.var_base_url = tk.StringVar(value=current_config.get("base_url", ""))
        self.var_timeout = tk.IntVar(value=int(current_config.get("timeout", 30)))
        self.var_max_retries = tk.IntVar(value=int(current_config.get("max_retries", 3)))
        self.var_verify_ssl = tk.BooleanVar(value=bool(current_config.get("verify_ssl", True)))
        self.var_remember_key = tk.BooleanVar(value=bool(current_config.get("remember_key", False)))
        self.var_show_key = tk.BooleanVar(value=False)

        # 主题下拉框（值用 Theme.value 字符串）
        theme_str = current_config.get("theme", "light")
        try:
            theme_value = Theme(theme_str).value
        except ValueError:
            theme_value = Theme.LIGHT.value
        self.var_theme = tk.StringVar(value=theme_value)

        self._build_ui()

        # 模态：grab 所有事件 + 等待窗口关闭
        self.grab_set()
        self.focus_set()

    # ---------- UI 构建 ----------

    def _build_ui(self) -> None:
        """构建对话框内部布局。"""
        font_ui = pick_ui_font()

        # === 上半部分：表单区域（用 grid，可滚动如果内容多）===
        form_frame = ttk.Frame(self, padding=(16, 16, 16, 8))
        form_frame.pack(side="top", fill="both", expand=True)
        form_frame.columnconfigure(1, weight=1)

        row = 0

        # API Key 行（带「显示明文」切换）
        ttk.Label(form_frame, text="API Key:", font=font_ui).grid(row=row, column=0, sticky="w", pady=6)
        key_frame = ttk.Frame(form_frame)
        key_frame.grid(row=row, column=1, sticky="ew", pady=6)
        key_frame.columnconfigure(0, weight=1)
        self.entry_api_key = ttk.Entry(
            key_frame, textvariable=self.var_api_key, show="*", font=font_ui
        )
        self.entry_api_key.grid(row=0, column=0, sticky="ew")
        self.btn_show = ttk.Checkbutton(
            key_frame,
            text="显示",
            variable=self.var_show_key,
            command=self._toggle_show_key,
        )
        self.btn_show.grid(row=0, column=1, padx=(6, 0))
        row += 1

        # Base URL
        ttk.Label(form_frame, text="Base URL:", font=font_ui).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(form_frame, textvariable=self.var_base_url, font=font_ui).grid(
            row=row, column=1, sticky="ew", pady=6
        )
        row += 1

        # 超时（秒）
        ttk.Label(form_frame, text="超时（秒）:", font=font_ui).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Spinbox(
            form_frame, from_=1, to=300, textvariable=self.var_timeout, width=10, font=font_ui
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # 重试次数
        ttk.Label(form_frame, text="重试次数:", font=font_ui).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Spinbox(
            form_frame, from_=0, to=10, textvariable=self.var_max_retries, width=10, font=font_ui
        ).grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # 校验 SSL（ttk.Checkbutton 不支持 font 选项，用主题默认字体）
        ttk.Checkbutton(
            form_frame, text="校验 SSL 证书（自签证书请取消）", variable=self.var_verify_ssl
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        # 记住 API Key（同上）
        ttk.Checkbutton(
            form_frame, text="记住 API Key（明文存本地，仅演示用）", variable=self.var_remember_key
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        # 主题
        ttk.Label(form_frame, text="主题:", font=font_ui).grid(row=row, column=0, sticky="w", pady=6)
        theme_choices = [
            (t.value, THEME_LABELS[t]) for t in (Theme.LIGHT, Theme.DARK, Theme.SYSTEM)
        ]
        theme_combo = ttk.Combobox(
            form_frame,
            textvariable=self.var_theme,
            values=[label for _v, label in theme_choices],
            state="readonly",
            width=20,
            font=font_ui,
        )
        # 把展示文字映射到内部 value（这样用户在 UI 看到的是「亮色/暗色/跟随系统」）
        self._theme_display_to_value = {label: v for v, label in theme_choices}
        theme_combo.set(THEME_LABELS[Theme(self.var_theme.get())])
        theme_combo.grid(row=row, column=1, sticky="w", pady=6)
        row += 1

        # 提示
        hint = ttk.Label(
            form_frame,
            text="提示：留空 API Key / Base URL 时，SDK 会自动读取 .env 或环境变量",
            foreground="#7f8c8d",
            font=font_ui,
            wraplength=420,
        )
        hint.grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 4))

        # === 下半部分：按钮栏（用 pack side=bottom，绝对在底部）===
        # 用一个高对比背景的 Frame 装按钮，确保视觉上独立、显眼
        btn_bar = tk.Frame(self, bg="#f0f0f0", height=70)
        btn_bar.pack(side="bottom", fill="x")
        btn_bar.pack_propagate(False)  # 固定高度，不被按钮撑变形

        # 用 tk.Button（不是 ttk），强制带 3D 边框，绝对可见
        save_btn = tk.Button(
            btn_bar,
            text="💾  保存",
            command=self._on_save_click,
            width=14,
            height=2,
            font=font_ui,
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            relief="raised",
            bd=2,
            cursor="hand2",
        )
        save_btn.pack(side="right", padx=(8, 16), pady=12)

        # 左侧：检查更新按钮（不关闭对话框就触发）
        update_btn = tk.Button(
            btn_bar,
            text="🔄  检查更新",
            command=self._on_check_update_click,
            width=14,
            height=2,
            font=font_ui,
            bg="#2196F3",
            fg="white",
            activebackground="#1976D2",
            relief="raised",
            bd=2,
            cursor="hand2",
        )
        update_btn.pack(side="left", padx=(16, 8), pady=12)

        cancel_btn = tk.Button(
            btn_bar,
            text="取消",
            command=self._on_cancel,
            width=10,
            height=2,
            font=font_ui,
            bg="#e0e0e0",
            activebackground="#d0d0d0",
            relief="raised",
            bd=2,
            cursor="hand2",
        )
        cancel_btn.pack(side="right", padx=8, pady=12)

        # 默认焦点在保存按钮上
        save_btn.focus_set()
        # Enter 触发保存
        self.bind("<Return>", lambda _e: self._on_save_click())
        # Escape 触发取消
        self.bind("<Escape>", lambda _e: self._on_cancel())

    # ---------- 行为 ----------

    def _toggle_show_key(self) -> None:
        """切换 API Key 输入框的显示模式（明文 / 密文）。"""
        self.entry_api_key.configure(show="" if self.var_show_key.get() else "*")

    def _on_cancel(self) -> None:
        """点取消：直接关闭窗口，不调用回调。"""
        self.destroy()

    def _on_check_update_click(self) -> None:
        """点检查更新：触发回调（不关闭对话框，让用户在结果对话框出现后再处理）。"""
        try:
            self.on_check_update()
        except Exception:  # noqa: BLE001
            pass

    def _on_save_click(self) -> None:
        """点保存：校验 → 回调 → 关闭。"""
        # 校验数字字段
        try:
            timeout = int(self.var_timeout.get())
            max_retries = int(self.var_max_retries.get())
        except (ValueError, tk.TclError):
            messagebox.showerror("输入有误", "超时和重试次数必须是整数", parent=self)
            return

        if timeout < 1:
            messagebox.showerror("输入有误", "超时必须 ≥ 1 秒", parent=self)
            return
        if max_retries < 0:
            messagebox.showerror("输入有误", "重试次数不能为负", parent=self)
            return

        new_config = {
            "api_key": self.var_api_key.get().strip(),
            "base_url": self.var_base_url.get().strip(),
            "timeout": timeout,
            "max_retries": max_retries,
            "verify_ssl": bool(self.var_verify_ssl.get()),
            "remember_key": bool(self.var_remember_key.get()),
            "theme": self._theme_display_to_value.get(self.var_theme.get(), Theme.LIGHT.value),
        }

        # 写本地（容错，失败也继续）
        save_config(new_config)

        # 通知主窗口
        if self.on_save is not None:
            try:
                self.on_save(new_config)
            except Exception as exc:  # noqa: BLE001 —— 防止回调异常阻断关闭
                messagebox.showerror(
                    "应用设置失败", f"回调函数抛错：{exc}\n\n请检查代码", parent=self
                )

        self.destroy()