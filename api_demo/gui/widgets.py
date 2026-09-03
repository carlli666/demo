"""
api_demo.gui.widgets
~~~~~~~~~~~~~~~~~~~~

左右两个面板：RequestPanel（构造请求） 和 ResponsePanel（展示响应）。

RequestPanel 负责收集和校验所有输入，校验失败时抛 ValueError（由主线程捕获弹框）。
ResponsePanel 是只读展示，所有写入走封装函数以正确切换 Text state。
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    BODY_TEXT_HEIGHT,
    COLOR_ERROR,
    COLOR_MUTED,
    COLOR_SUCCESS,
    HEADERS_NOTE,
    HEADERS_ROWS,
    HTTP_METHODS,
    METHODS_WITH_BODY,
    PARAMS_ROWS,
    pick_mono_font,
    pick_ui_font,
)


# ==================== 请求面板 ====================


class RequestPanel(ttk.Frame):
    """
    左侧请求构造面板。

    控件：
      - Method 下拉
      - Path 输入框
      - Params / Headers / Body 三页签（ttk.Notebook）
      - 发送按钮（由主窗口放在外面，不在这里）

    公开方法：
      - collect_input(): 收集并校验，返回 dict；校验失败抛 ValueError
      - set_method(method): 切换方法并联动 Body 页启用态
      - fill_example(): 一键填入示例请求
      - clear(): 清空所有输入
    """

    def __init__(self, master: tk.Misc, on_send: callable):
        super().__init__(master)
        self.on_send = on_send  # 「发送」按钮的事件回调（主窗口传进来）

        self._body_auto_filled = False  # Body 是否已被自动填过一次示例

        self.var_method = tk.StringVar(value=HTTP_METHODS)
        self.var_path = tk.StringVar()
        self.body_text: Optional[tk.Text] = None

        # Params / Headers 的 (key_entry, value_entry) 列表
        self.param_rows: List[Tuple[tk.Entry, tk.Entry]] = []
        self.header_rows: List[Tuple[tk.Entry, tk.Entry]] = []

        self._build_ui()

    # ---------- 构建 ----------

    def _build_ui(self) -> None:
        """构建请求面板 UI。"""
        font_ui = pick_ui_font()
        mono = pick_mono_font()

        # 让 grid 自适应
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Notebook 区可伸缩

        # 第 0 行：方法 + 路径
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="方法:", font=font_ui).grid(row=0, column=0, padx=(0, 6))
        self.cmb_method = ttk.Combobox(
            top,
            textvariable=self.var_method,
            values=HTTP_METHODS,
            state="readonly",
            width=10,
            font=font_ui,
        )
        self.cmb_method.grid(row=0, column=1, sticky="w")
        self.cmb_method.bind("<<ComboboxSelected>>", self._on_method_change)

        ttk.Label(top, text="路径:", font=font_ui).grid(row=0, column=2, padx=(12, 6))
        self.entry_path = ttk.Entry(top, textvariable=self.var_path, font=font_ui)
        self.entry_path.grid(row=0, column=3, sticky="ew")

        # 启动预填
        self.var_path.set("/users/123")

        # 第 1 行：分隔条
        ttk.Separator(self, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=4)

        # 第 2 行：Notebook（Params / Headers / Body）
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=2, column=0, sticky="nsew")

        self._build_params_tab(self.notebook, font_ui)
        self._build_headers_tab(self.notebook, font_ui)
        self._build_body_tab(self.notebook, font_ui)

        # 第 3 行：发送按钮 + 状态
        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(1, weight=1)

        self.btn_send = ttk.Button(bottom, text="🚀  发送请求", command=self.on_send)
        self.btn_send.grid(row=0, column=0, sticky="w")

        self.status_label = ttk.Label(bottom, text="就绪", font=font_ui, foreground=COLOR_MUTED)
        self.status_label.grid(row=0, column=1, sticky="w", padx=(12, 0))

    def _build_params_tab(self, parent: tk.Misc, font: tuple) -> None:
        """构建 Params 页：固定 5 行 key/value Entry。"""
        frame = ttk.Frame(parent, padding=8)
        parent.add(frame, text=f"Params ({PARAMS_ROWS} 行)")

        # 表头
        header = ttk.Frame(frame)
        header.pack(fill="x")
        ttk.Label(header, text="键", width=20, font=font).pack(side="left", padx=(0, 4))
        ttk.Label(header, text="值", font=font).pack(side="left")

        # 输入行
        rows_box = ttk.Frame(frame)
        rows_box.pack(fill="both", expand=True, pady=(4, 0))

        for i in range(PARAMS_ROWS):
            row = ttk.Frame(rows_box)
            row.pack(fill="x", pady=2)
            k = ttk.Entry(row, width=22, font=font)
            v = ttk.Entry(row, font=font)
            k.pack(side="left", padx=(0, 4))
            v.pack(side="left", fill="x", expand=True)
            self.param_rows.append((k, v))

    def _build_headers_tab(self, parent: tk.Misc, font: tuple) -> None:
        """构建 Headers 页：固定 3 行 + 顶部灰字提示。"""
        frame = ttk.Frame(parent, padding=8)
        parent.add(frame, text=f"Headers ({HEADERS_ROWS} 行)")

        ttk.Label(
            frame, text=HEADERS_NOTE, foreground=COLOR_MUTED, font=font, wraplength=400
        ).pack(anchor="w", pady=(0, 6))

        header = ttk.Frame(frame)
        header.pack(fill="x")
        ttk.Label(header, text="键", width=20, font=font).pack(side="left", padx=(0, 4))
        ttk.Label(header, text="值", font=font).pack(side="left")

        rows_box = ttk.Frame(frame)
        rows_box.pack(fill="both", expand=True, pady=(4, 0))

        for i in range(HEADERS_ROWS):
            row = ttk.Frame(rows_box)
            row.pack(fill="x", pady=2)
            k = ttk.Entry(row, width=22, font=font)
            v = ttk.Entry(row, font=font)
            k.pack(side="left", padx=(0, 4))
            v.pack(side="left", fill="x", expand=True)
            self.header_rows.append((k, v))

    def _build_body_tab(self, parent: tk.Misc, font: tuple) -> None:
        """构建 Body 页：等宽文本框 + 「格式化」按钮。"""
        frame = ttk.Frame(parent, padding=8)
        parent.add(frame, text="Body")

        # 顶部说明
        ttk.Label(
            frame,
            text="请求体（JSON），仅 POST/PUT/PATCH 生效；GET/DELETE 会被忽略",
            foreground=COLOR_MUTED,
            font=font,
        ).pack(anchor="w", pady=(0, 4))

        # 文本框 + 滚动条
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill="both", expand=True)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.body_text = tk.Text(
            text_frame,
            height=BODY_TEXT_HEIGHT,
            wrap="none",
            font=font,
            undo=True,
        )
        self.body_text.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(text_frame, orient="vertical", command=self.body_text.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.body_text.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(text_frame, orient="horizontal", command=self.body_text.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.body_text.configure(xscrollcommand=scroll_x.set)

        # 「格式化 JSON」按钮
        btn_bar = ttk.Frame(frame)
        btn_bar.pack(fill="x", pady=(6, 0))
        ttk.Button(btn_bar, text="格式化 JSON", command=self._format_body).pack(side="left")

    # ---------- 行为 ----------

    def _on_method_change(self, _event: Optional[tk.Event] = None) -> None:
        """切换方法时，禁用或启用 Body 页（视觉上靠 tab state 实现）。"""
        # ttk.Notebook 不支持直接禁用 tab，但可以在状态标签提示
        # 这里用状态标签 + Body 文本框 state 联动
        if self.body_text is None:
            return
        if self.var_method.get() in METHODS_WITH_BODY:
            self.body_text.configure(state="normal")
            self.status_label.configure(text="就绪")
        else:
            self.body_text.configure(state="disabled")
            self.status_label.configure(text=f"{self.var_method.get()} 不需要 Body")

    def _format_body(self) -> None:
        """把 Body 文本框内容格式化为标准 JSON（缩进 2 空格）。"""
        if self.body_text is None:
            return
        raw = self.body_text.get("1.0", "end").strip()
        if not raw:
            return
        try:
            obj = json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            from tkinter import messagebox
            messagebox.showerror("JSON 格式错误", f"无法解析：{exc}", parent=self)
            return
        formatted = json.dumps(obj, ensure_ascii=False, indent=2)
        self.body_text.configure(state="normal")
        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", formatted)
        if self.var_method.get() not in METHODS_WITH_BODY:
            self.body_text.configure(state="disabled")

    def fill_example(self) -> None:
        """一键填入示例请求（GET /todos/1）。"""
        from .constants import get_example_request

        example = get_example_request()
        self.var_method.set(example["method"])
        self.var_path.set(example["path"])

        # Params
        for i, (k, v) in enumerate(self.param_rows):
            k.delete(0, "end")
            v.delete(0, "end")
        for i, (key, val) in enumerate(example["params"]):
            if i >= len(self.param_rows):
                break
            self.param_rows[i][0].insert(0, key)
            self.param_rows[i][1].insert(0, val)

        # Headers（不填示例，提示有默认头）
        for k_entry, v_entry in self.header_rows:
            k_entry.delete(0, "end")
            v_entry.delete(0, "end")

        # Body
        if self.body_text is not None:
            self.body_text.configure(state="normal")
            self.body_text.delete("1.0", "end")
            self.body_text.insert("1.0", example["body"])
            self._body_auto_filled = True

        self._on_method_change()
        self.status_label.configure(text="已填入示例，改成你自己的地址后点「发送」")

    def clear(self) -> None:
        """清空所有输入。"""
        self.var_path.set("")
        for k_entry, v_entry in self.param_rows:
            k_entry.delete(0, "end")
            v_entry.delete(0, "end")
        for k_entry, v_entry in self.header_rows:
            k_entry.delete(0, "end")
            v_entry.delete(0, "end")
        if self.body_text is not None:
            self.body_text.configure(state="normal")
            self.body_text.delete("1.0", "end")
        self._body_auto_filled = False
        self.status_label.configure(text="已清空")

    # ---------- 收集与校验 ----------

    def collect_input(self) -> Dict[str, Any]:
        """
        收集界面输入，校验后返回。

        :return: dict，键: method / path / params / headers / body
        :raises ValueError: 校验失败（路径空 / Body JSON 不合法）
        """
        method = self.var_method.get()
        path = self.var_path.get().strip()
        if not path:
            raise ValueError("路径不能为空")

        # 收集 Params（忽略空 key）
        params: List[Tuple[str, str]] = []
        for k_entry, v_entry in self.param_rows:
            key = k_entry.get().strip()
            val = v_entry.get().strip()
            if key:
                params.append((key, val))

        # 收集 Headers（忽略空 key）
        headers: List[Tuple[str, str]] = []
        for k_entry, v_entry in self.header_rows:
            key = k_entry.get().strip()
            val = v_entry.get().strip()
            if key:
                headers.append((key, val))

        # Body（仅在方法支持时才解析）
        body_text = ""
        body_json: Any = None
        if self.body_text is not None and method in METHODS_WITH_BODY:
            body_text = self.body_text.get("1.0", "end").strip()
            if body_text:
                try:
                    body_json = json.loads(body_text)
                except (ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"Body 不是合法的 JSON：{exc}") from exc

        return {
            "method": method,
            "path": path,
            "params": params,
            "headers": headers,
            "body_text": body_text,
            "body_json": body_json,
        }


# ==================== 响应面板 ====================


class ResponsePanel(ttk.Frame):
    """
    右侧响应展示面板。

    公开方法：
      - display_text(text): 普通文本（成功响应）
      - display_error(text, status): 错误文本（红色）
      - set_status(status, elapsed_ms): 更新顶部状态行
      - get_text(): 取出当前文本（用于复制）
    """

    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        mono = pick_mono_font()
        font_ui = pick_ui_font()

        # 第 0 行：状态 + 耗时
        self.var_status = tk.StringVar(value="Status: —")
        self.var_elapsed = tk.StringVar(value="Time: —")

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top.columnconfigure(2, weight=1)

        self.lbl_status = ttk.Label(top, textvariable=self.var_status, font=font_ui)
        self.lbl_status.grid(row=0, column=0, sticky="w")
        self.lbl_elapsed = ttk.Label(
            top, textvariable=self.var_elapsed, font=font_ui, foreground=COLOR_MUTED
        )
        self.lbl_elapsed.grid(row=0, column=1, sticky="w", padx=(16, 0))

        # 第 1 行：响应文本
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.text = tk.Text(
            text_frame, wrap="none", font=mono, state="disabled", undo=False
        )
        self.text.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(text_frame, orient="horizontal", command=self.text.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.text.configure(xscrollcommand=scroll_x.set)

        # 配置 tag：用于错误着色
        self.text.tag_configure("error", foreground=COLOR_ERROR)
        self.text.tag_configure("meta", foreground=COLOR_MUTED)

        # 第 2 行：复制按钮
        btn_bar = ttk.Frame(self)
        btn_bar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(btn_bar, text="📋  复制响应", command=self._on_copy).pack(side="left")

    # ---------- 写入 ----------

    def _write(self, text: str, tag: Optional[str] = None) -> None:
        """内部统一写入函数：解锁 → 写 → 锁回。"""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        if tag:
            self.text.insert("1.0", text, tag)
        else:
            self.text.insert("1.0", text)
        self.text.configure(state="disabled")

    def display_text(self, text: str) -> None:
        """展示普通文本（成功响应 / 等待提示）。"""
        self._write(text)

    def display_error(self, text: str, status: Optional[int] = None) -> None:
        """展示错误文本（红色）。"""
        self._write(text, tag="error")

    def set_status(self, status: Optional[int], elapsed_ms: Optional[float] = None) -> None:
        """
        更新顶部状态行。

        :param status: HTTP 状态码；None 表示未知
        :param elapsed_ms: 耗时（毫秒）；None 表示未知
        """
        if status is None:
            self.var_status.set("Status: —")
            self.lbl_status.configure(foreground=COLOR_MUTED)
        else:
            self.var_status.set(f"Status: {status}")
            if 200 <= status < 300:
                self.lbl_status.configure(foreground=COLOR_SUCCESS)
            elif status >= 400:
                self.lbl_status.configure(foreground=COLOR_ERROR)
            else:
                self.lbl_status.configure(foreground=COLOR_MUTED)

        if elapsed_ms is None:
            self.var_elapsed.set("Time: —")
        else:
            self.var_elapsed.set(f"Time: {elapsed_ms:.0f} ms")

    # ---------- 复制 ----------

    def _on_copy(self) -> None:
        """把当前响应文本复制到剪贴板。"""
        content = self.text.get("1.0", "end").rstrip()
        if not content:
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        # 让剪贴板内容在窗口关闭后仍保留
        self.update()  # 确保更新到 X server

    def get_text(self) -> str:
        """返回当前响应文本（备用）。"""
        return self.text.get("1.0", "end").rstrip()