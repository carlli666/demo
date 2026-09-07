"""
api_demo.gui.app
~~~~~~~~~~~~~~~~

GUI 主窗口 + 线程调度 + 异常翻译 + main() 入口。

核心规则：
  - Tk 控件只能在主线程里访问
  - requests 调用必须放工作线程
  - 用 queue.Queue 跨线程传数据
  - 用 root.after(100, ...) 在主线程里轮询

工作线程用模块级函数 _worker 实现：拿不到 self，物理上避免误碰控件。
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

from api_demo import APIError, AuthError, Client, NotFoundError, RateLimitError, ServerError

from .constants import (
    COLOR_MUTED,
    FRIENDLY_ERROR_TEMPLATES,
    PAD_SM,
    WELCOME_TEXT,
    WINDOW_DEFAULT_SIZE,
    WINDOW_MIN_SIZE,
    pick_ui_font,
)
from .settings import SettingsDialog, load_config
from .theme import THEME_CYCLE, THEME_LABELS, Theme, ThemeManager
from .widgets import RequestPanel, ResponsePanel


# ==================== 跨线程工具 ====================


def format_json(data: Any) -> str:
    """
    把 Python 对象格式化成易读 JSON。

    中文不被转义（ensure_ascii=False），缩进 2 空格。
    遇到不可序列化对象时退回 str()，永不抛异常。

    :param data: 任意 Python 对象
    :return: 格式化后的字符串
    """
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(data)


def _pairs_to_dict(pairs: list) -> Dict[str, str]:
    """把 [(k, v), ...] 列表（保留顺序）转成 dict（同 key 后值覆盖前值）。"""
    result: Dict[str, str] = {}
    for k, v in pairs:
        if k:  # 防御：空键跳过
            result[k] = v
    return result


# ==================== 工作线程（模块级函数，绝不碰 Tk） ====================


def _worker(
    client: Client,
    params: Dict[str, Any],
    queue_out: "queue.Queue[Dict[str, Any]]",
) -> None:
    """
    在后台线程里调用 SDK 发请求，并把结果放进队列。

    ⚠️ 本函数禁止访问任何 Tk 控件，只能写：
      - 局部变量 `record`（response hook 写入）
      - 入参 `queue_out`（结果出口）

    :param client: 已创建好的 api_demo.Client 实例
    :param params: 界面收集到的请求参数（dict）
    :param queue_out: 把结果回传给主线程的队列
    """
    method = params["method"]
    path = params["path"]
    headers = _pairs_to_dict(params.get("headers", []))
    query_params = _pairs_to_dict(params.get("params", []))
    body_json = params.get("body_json")

    # 用 response hook 捕获状态码和耗时（同步 SDK 不返回这些）
    record: Dict[str, Any] = {}

    def hook(response, *args, **kwargs):
        record["status"] = response.status_code
        record["elapsed_ms"] = response.elapsed.total_seconds() * 1000
        return response

    client.session.hooks["response"].append(hook)
    start = time.time()

    try:
        extras: Dict[str, Any] = {}
        if headers:
            extras["headers"] = headers
        if query_params:
            extras["params"] = query_params

        # 按方法分发
        if method == "GET":
            data = client.get(path, **extras)
        elif method == "DELETE":
            data = client.delete(path, **extras)
        elif method == "POST":
            data = client.post(path, json=body_json, **extras)
        elif method == "PUT":
            data = client.put(path, json=body_json, **extras)
        else:  # PATCH
            data = client.patch(path, json=body_json, **extras)

        queue_out.put(
            {
                "ok": True,
                "data": data,
                "status": record.get("status"),
                "elapsed_ms": record.get(
                    "elapsed_ms", (time.time() - start) * 1000
                ),
            }
        )
    except APIError as exc:
        # SDK 异常体系（Auth/NotFound/RateLimit/Server 都是它的子类）
        queue_out.put(
            {
                "ok": False,
                "exc": exc,
                "status": exc.status_code,
                "elapsed_ms": (time.time() - start) * 1000,
            }
        )
    except Exception as exc:  # noqa: BLE001 —— 兜底：绝不让线程异常静默死掉
        queue_out.put(
            {
                "ok": False,
                "exc": exc,
                "status": None,
                "elapsed_ms": (time.time() - start) * 1000,
            }
        )
    finally:
        # 用完摘掉钩子，避免同一个 client 越挂越多
        try:
            client.session.hooks["response"].remove(hook)
        except ValueError:
            pass


# ==================== 主窗口 ====================


class App:
    """
    主窗口控制器。

    生命周期：实例化 → run() → 窗口关闭 → close()。

    :param root: 已创建的 tk.Tk 根窗口（由 main() 创建并传入）
    """

    # 友好错误信息：key = 异常类名（避免在工作线程里 import Client 时循环依赖）
    _FRIENDLY_ERROR = FRIENDLY_ERROR_TEMPLATES

    def __init__(self, root: tk.Tk):
        self.root = root
        self.client: Optional[Client] = None  # 懒加载
        self.config: Dict[str, Any] = load_config()
        self.result_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()

        # Windows 高 DPI（仅 Windows 且不强制要求）
        if sys.platform.startswith("win"):
            try:
                from ctypes import windll

                windll.shcore.SetProcessDpiAwareness(1)
            except Exception:  # noqa: BLE001
                pass

        # 创建主题管理器（创建后立即应用，避免首次绘制闪烁）
        self.theme_manager = ThemeManager(self.root)

        self._build_window()
        self._wire_events()

        # 应用持久化的主题偏好
        pref_str = self.config.get("theme", "light")
        try:
            pref_theme = Theme(pref_str)
        except ValueError:
            pref_theme = Theme.LIGHT
        self.theme_manager.apply_preference(pref_theme)
        self._update_theme_button()

        # 启动时显示欢迎语
        self.response_panel.display_text(WELCOME_TEXT)
        self.status_bar.set("就绪 — 尚未连接服务器")

    # ---------- 构建 ----------

    def _build_window(self) -> None:
        """构建窗口主体。"""
        self.root.title("intelligent assistant")
        self.root.geometry(WINDOW_DEFAULT_SIZE)
        self.root.minsize(*WINDOW_MIN_SIZE)

        font_ui = pick_ui_font()

        # === 工具条 ===
        toolbar = ttk.Frame(self.root, padding=(PAD_SM, PAD_SM))
        toolbar.pack(fill="x")

        # 左侧按钮
        ttk.Button(toolbar, text="⚙  设置", command=self._open_settings).pack(
            side="left", padx=(0, PAD_SM)
        )
        ttk.Button(toolbar, text="📄  使用示例", command=self._on_example).pack(
            side="left", padx=PAD_SM
        )
        ttk.Button(toolbar, text="🧹  清空", command=self._on_clear).pack(
            side="left", padx=PAD_SM
        )

        # 右侧：主题切换 + 当前地址
        right = ttk.Frame(toolbar)
        right.pack(side="right")
        self.btn_theme = ttk.Button(
            right, text="☀ 亮色", width=10, command=self._on_theme_toggle
        )
        self.btn_theme.pack(side="right", padx=(PAD_SM, 0))

        self.var_current = tk.StringVar(value="当前地址: （未配置）")
        ttk.Label(
            right, textvariable=self.var_current, font=font_ui, style="Muted.TLabel"
        ).pack(side="right", padx=(0, PAD_SM))

        # === 主体：左右两个面板 ===
        body = ttk.Panedwindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=PAD_SM, pady=(0, PAD_SM))

        self.request_panel = RequestPanel(body, theme_manager=self.theme_manager, on_send=self.send_request)
        body.add(self.request_panel, weight=1)

        self.response_panel = ResponsePanel(body, theme_manager=self.theme_manager)
        body.add(self.response_panel, weight=1)

        # === 状态栏 ===
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill="x", side="bottom")

    def _wire_events(self) -> None:
        """绑定窗口事件。"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 主题 ----------

    def _on_theme_toggle(self) -> None:
        """工具栏主题按钮：循环切换 light → dark → system → light。"""
        new_theme = self.theme_manager.toggle()
        # 持久化
        self.config["theme"] = new_theme.value
        self._persist_config()
        self._update_theme_button()
        # 主题切换后重画响应区状态色
        self.response_panel.set_status(None, None)

    def _update_theme_button(self) -> None:
        """更新主题切换按钮的文字。"""
        icons = {
            Theme.LIGHT: "☀",
            Theme.DARK: "🌙",
            Theme.SYSTEM: "🖥",
        }
        icon = icons.get(self.theme_manager.current, "☀")
        self.btn_theme.configure(text=f"{icon} {THEME_LABELS[self.theme_manager.preference]}")

    def _persist_config(self) -> None:
        """把当前 config（除了 api_key 外）写到磁盘。"""
        from .settings import save_config

        save_config(self.config)

    # ---------- Client 管理 ----------

    def _get_client(self) -> Client:
        """
        懒加载获取 Client。第一次发送时才创建；配置变更后会被置空重建。

        :return: Client 实例
        :raises ValueError: 配置不完整（API Key 或 Base URL 缺失）
        """
        if self.client is None:
            self.client = Client(
                api_key=self.config.get("api_key") or None,
                base_url=self.config.get("base_url") or None,
                timeout=int(self.config.get("timeout", 30)),
                max_retries=int(self.config.get("max_retries", 3)),
                verify_ssl=bool(self.config.get("verify_ssl", True)),
            )
            self.status_bar.set(f"已连接：{self.client.base_url}")
            self.var_current.set(f"当前地址: {self.client.base_url}")
        return self.client

    def _apply_settings(self, new_config: Dict[str, Any]) -> None:
        """设置保存后回调：关掉旧 client，让下次发送重建。"""
        if self.client is not None:
            try:
                self.client.close()
            except Exception:  # noqa: BLE001
                pass
            self.client = None
        self.config.update(new_config)
        # 主题变化立即生效
        theme_str = self.config.get("theme", "light")
        try:
            pref_theme = Theme(theme_str)
            if pref_theme != self.theme_manager.preference:
                self.theme_manager.apply_preference(pref_theme)
                self._update_theme_button()
        except ValueError:
            pass
        # 更新「当前地址」显示（即使还没真正连上）
        base = self.config.get("base_url") or "（未配置）"
        self.var_current.set(f"当前地址: {base}")
        self.status_bar.set("设置已更新，下次请求生效")

    # ---------- UI 事件 ----------

    def _open_settings(self) -> None:
        """打开设置对话框（模态）。"""
        dlg = SettingsDialog(self.root, self.config, on_save=self._apply_settings)
        self.root.wait_window(dlg)

    def _on_example(self) -> None:
        """一键填入示例请求。"""
        self.request_panel.fill_example()
        self.status_bar.set("已填入示例，配置好后点「发送」")

    def _on_clear(self) -> None:
        """清空输入和响应。"""
        self.request_panel.clear()
        self.response_panel.display_text(WELCOME_TEXT)
        self.response_panel.set_status(None, None)
        self.status_bar.set("已清空")

    def _on_close(self) -> None:
        """窗口关闭：先关掉 SDK 的连接池，再销毁窗口。"""
        if self.client is not None:
            try:
                self.client.close()
            except Exception:  # noqa: BLE001
                pass
            self.client = None
        self.root.destroy()

    # ---------- 发送请求（主线程） ----------

    def send_request(self) -> None:
        """点击「发送请求」：校验 → 起线程 → 等待态。"""
        # 1) 懒加载客户端
        try:
            client = self._get_client()
        except ValueError as exc:
            messagebox.showwarning(
                "配置不完整",
                f"{exc}\n\n请点击左上角「⚙ 设置」填写 API Key 和 Base URL。",
                parent=self.root,
            )
            self.status_bar.set("❌ 配置不完整，请先点「设置」")
            return

        # 2) 收集并校验输入
        try:
            params = self.request_panel.collect_input()
        except ValueError as exc:
            messagebox.showerror("输入有误", str(exc), parent=self.root)
            self.status_bar.set(f"❌ {exc}")
            return

        # 3) 进入等待态
        self.request_panel.btn_send.configure(state="disabled")
        self.request_panel.status_label.configure(text="请求中…")
        self.status_bar.set("请求中…")
        self.response_panel.set_status(None, None)
        self.response_panel.display_text("正在请求，请稍候…")

        # 4) 起工作线程
        thread = threading.Thread(
            target=_worker,
            args=(client, params, self.result_queue),
            daemon=True,  # 关窗口时不卡进程退出
        )
        thread.start()

        # 5) 开始轮询
        self.root.after(100, self._poll_result)

    # ---------- 主线程轮询 ----------

    def _poll_result(self) -> None:
        """
        每 100 毫秒检查一次队列；拿到结果就更新界面。

        「点发送才开始轮询，拿到结果就停」：空闲时零开销。
        """
        try:
            result = self.result_queue.get_nowait()
        except queue.Empty:
            # 还没好 → 再等 100ms（按钮已 disabled，不会产生多条 after 链）
            self.root.after(100, self._poll_result)
            return

        # 拿到结果：主线程，可以放心操作控件
        if result.get("ok"):
            self._show_success(result)
        else:
            self._show_failure(result)

        # 恢复按钮（无论成败都恢复）
        self.request_panel.btn_send.configure(state="normal")
        self.request_panel.status_label.configure(text="就绪")

    # ---------- 结果展示 ----------

    def _show_success(self, result: Dict[str, Any]) -> None:
        """展示成功响应。"""
        data = result.get("data")
        status = result.get("status")
        elapsed = result.get("elapsed_ms")

        self.response_panel.set_status(status, elapsed)
        text = format_json(data)
        # 提示非 dict / 空响应
        if isinstance(data, dict) and "raw" in data and len(data) == 1:
            text = "（响应不是 JSON，按原文显示）\n\n" + data["raw"]
        elif data == {} or data is None:
            text = "（响应体为空）"
        self.response_panel.display_text(text)
        if status is not None and 200 <= status < 300:
            self.status_bar.set(f"✅ 请求成功 — {status} · {elapsed:.0f}ms")
        else:
            self.status_bar.set(f"请求完成 — {status}")

    def _show_failure(self, result: Dict[str, Any]) -> None:
        """把异常翻译成小白能看懂的提示。"""
        exc = result.get("exc")
        status = result.get("status")
        elapsed = result.get("elapsed_ms")

        self.response_panel.set_status(status, elapsed)

        # 按异常类名查友好信息
        cls_name = type(exc).__name__
        friendly = self._FRIENDLY_ERROR.get(cls_name, "请求失败")

        lines = [f"❌ {friendly}", "", f"详情：{exc}"]
        # 如果异常对象有 response（如 APIError），把服务器返回也展示出来
        if isinstance(exc, APIError) and getattr(exc, "response", None) is not None:
            lines += ["", "服务器返回内容：", format_json(exc.response)]
        elif getattr(exc, "response", None) is not None:
            lines += ["", "服务器返回内容：", format_json(exc.response)]

        self.response_panel.display_error("\n".join(lines), status)
        self.status_bar.set(f"❌ {friendly}")

    # ---------- 运行 ----------

    def run(self) -> None:
        """进入 Tk 主循环。"""
        self.root.mainloop()


# ==================== 状态栏 ====================


class StatusBar(ttk.Frame):
    """底部状态栏：左边文字提示，右边可扩展。"""

    def __init__(self, master: tk.Misc):
        super().__init__(master, relief="sunken", padding=(8, 3))
        self.var_text = tk.StringVar(value="")
        font_ui = pick_ui_font()
        self.label = ttk.Label(
            self, textvariable=self.var_text, font=font_ui, foreground=COLOR_MUTED
        )
        self.label.pack(side="left")

    def set(self, text: str) -> None:
        """更新文字。"""
        self.var_text.set(text)


# ==================== 入口 ====================


def main() -> None:
    """GUI 程序入口。"""
    root = tk.Tk()
    # ttk 主题
    try:
        style = ttk.Style(root)
        # 在 Windows / macOS 上 'clam' 通常比默认主题更好看
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except tk.TclError:
        pass

    app = App(root)
    app.run()


if __name__ == "__main__":
    main()