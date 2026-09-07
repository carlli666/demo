"""
api_demo.gui.updater_dialog
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

升级相关的 3 个对话框：

- UpdateAvailableDialog：发现新版本
- DownloadProgressDialog：下载进度
- UpdateReadyDialog：下载完成、准备重启

全部继承 tk.Toplevel，模态。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from api_demo import __version__
from api_demo.updater import ReleaseInfo

from .constants import pick_ui_font


# ==================== 1. 发现新版本 ====================


class UpdateAvailableDialog(tk.Toplevel):
    """发现新版本时弹出，让用户选「立即更新 / 稍后 / 跳过」。"""

    def __init__(
        self,
        parent: tk.Misc,
        release: ReleaseInfo,
        on_install: Callable[[], None],
        on_skip: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.release = release
        self.on_install = on_install
        self.on_skip = on_skip or (lambda: None)

        self.title("🎉 发现新版本")
        self.geometry("520x420")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        font_ui = pick_ui_font()

        # 标题
        ttk.Label(
            self,
            text=f"发现新版本 v{release.version}",
            font=(font_ui[0], 13, "bold"),
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, PAD_SM))

        # 当前版本 → 新版本
        current_line = f"当前版本：v{__version__}    →    新版本：v{release.version}"
        ttk.Label(self, text=current_line, font=font_ui).pack(anchor="w", padx=PAD_LG)

        # asset 大小
        if release.size_bytes > 0:
            size_mb = release.size_bytes / 1024 / 1024
            ttk.Label(
                self,
                text=f"文件大小：约 {size_mb:.1f} MB",
                font=font_ui,
                foreground="#64748b",
            ).pack(anchor="w", padx=PAD_LG, pady=(2, 0))

        # 更新说明
        notes_frame = ttk.LabelFrame(self, text="更新说明", padding=PAD_SM)
        notes_frame.pack(fill="both", expand=True, padx=PAD_LG, pady=PAD_MD)

        text = tk.Text(
            notes_frame,
            wrap="word",
            height=10,
            font=font_ui,
            relief="flat",
            borderwidth=0,
        )
        text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(notes_frame, orient="vertical", command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)

        notes = release.release_notes.strip() or "（作者没写更新说明）"
        text.insert("1.0", notes)
        text.configure(state="disabled")  # 只读

        # 按钮栏
        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))

        ttk.Button(
            btn_bar, text="跳过此版本", command=self._on_skip_click
        ).pack(side="left")

        ttk.Button(
            btn_bar, text="稍后", command=self.destroy
        ).pack(side="right", padx=(PAD_SM, 0))

        self.btn_install = ttk.Button(
            btn_bar,
            text="立即更新",
            command=self._on_install_click,
        )
        self.btn_install.pack(side="right", padx=(0, PAD_SM))

        self.bind("<Escape>", lambda _e: self.destroy())

    def _on_install_click(self) -> None:
        """点立即更新：关自己 + 触发下载（由 App 启动下载流程）。"""
        self.btn_install.configure(state="disabled", text="准备中...")
        self.destroy()
        self.on_install()

    def _on_skip_click(self) -> None:
        self.on_skip()
        self.destroy()


# ==================== 2. 下载进度 ====================


class DownloadProgressDialog(tk.Toplevel):
    """下载进度条 + 速度 + 取消按钮。"""

    def __init__(
        self,
        parent: tk.Misc,
        release: ReleaseInfo,
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.on_cancel = on_cancel or (lambda: None)
        self.cancelled = False

        self.title(f"下载 v{release.version}")
        self.geometry("460x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        font_ui = pick_ui_font()

        # 状态文字
        self.var_status = tk.StringVar(value=f"正在下载 v{release.version}...")
        ttk.Label(self, textvariable=self.var_status, font=font_ui).pack(
            anchor="w", padx=PAD_LG, pady=(PAD_LG, PAD_SM)
        )

        # 进度条
        self.var_progress = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(
            self,
            mode="determinate",
            maximum=100,
            variable=self.var_progress,
        )
        self.progress.pack(fill="x", padx=PAD_LG)

        # 详细信息
        self.var_detail = tk.StringVar(value="0 B / 0 B    ·    -- MB/s")
        ttk.Label(
            self, textvariable=self.var_detail, font=font_ui, foreground="#64748b"
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_SM, 0))

        # 取消按钮
        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=PAD_LG, pady=(PAD_MD, PAD_LG))
        ttk.Button(btn_bar, text="取消", command=self._on_cancel_click).pack(side="right")

        self.bind("<Escape>", lambda _e: self._on_cancel_click())

    def update_progress(self, done: int, total: int) -> None:
        """由 download_to 的 progress_cb 调用，在工作线程里。"""
        if self.cancelled:
            return
        # total 可能为 0（服务器没给 Content-Length）→ indeterminate 模式
        if total <= 0:
            self.var_progress.set(50)  # 一直显示 50%
            self.var_detail.set(f"{_format_size(done)}    ·    未知总大小")
        else:
            pct = done * 100 / total
            self.var_progress.set(pct)
            self.var_detail.set(f"{_format_size(done)} / {_format_size(total)}")

    def mark_complete(self) -> None:
        self.var_progress.set(100)
        self.var_status.set("下载完成，准备安装")

    def _on_cancel_click(self) -> None:
        self.cancelled = True
        self.destroy()
        self.on_cancel()


# ==================== 3. 下载完成、准备重启 ====================


class UpdateReadyDialog(tk.Toplevel):
    """下载完成。让用户选「立即重启」或「稍后重启」。"""

    def __init__(
        self,
        parent: tk.Misc,
        release: ReleaseInfo,
        on_install_now: Callable[[], None],
        on_later: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.on_install_now = on_install_now
        self.on_later = on_later or (lambda: None)

        self.title("✅ 更新已就绪")
        self.geometry("440x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        font_ui = pick_ui_font()

        ttk.Label(
            self,
            text=f"v{release.version} 已下载完成",
            font=(font_ui[0], 12, "bold"),
        ).pack(anchor="w", padx=PAD_LG, pady=(PAD_LG, PAD_SM))

        ttk.Label(
            self,
            text="应用将在重启后自动升级到新版本。\n升级过程会关闭当前窗口，几秒钟后自动打开新版。",
            font=font_ui,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", padx=PAD_LG, pady=(0, PAD_MD))

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=PAD_LG, pady=(0, PAD_LG))

        ttk.Button(
            btn_bar, text="稍后重启", command=self._on_later_click
        ).pack(side="right", padx=(PAD_SM, 0))

        ttk.Button(
            btn_bar,
            text="立即重启",
            command=self._on_install_now_click,
        ).pack(side="right", padx=(0, PAD_SM))

        self.bind("<Escape>", lambda _e: self._on_later_click())

    def _on_install_now_click(self) -> None:
        self.destroy()
        self.on_install_now()

    def _on_later_click(self) -> None:
        self.destroy()
        self.on_later()


# ==================== 工具函数 ====================


def _format_size(n: int) -> str:
    """字节数 → 人类可读（KB / MB / GB）。"""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / 1024 / 1024:.2f} MB"
    return f"{n / 1024 / 1024 / 1024:.2f} GB"


# 间距常量（避免从 constants 导入以减少耦合）
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16