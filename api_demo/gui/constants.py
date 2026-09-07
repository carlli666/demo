"""
api_demo.gui.constants
~~~~~~~~~~~~~~~~~~~~~~~

GUI 模块用到的常量、文案、配色、示例数据。

把所有「文字 / 颜色 / 字号 / 默认值」集中在这里，方便后续修改和翻译。

主题相关常量（PALETTE_LIGHT / PALETTE_DARK / METHOD_COLORS）由 theme.py 读取并应用。
"""
from __future__ import annotations

import sys
import tkinter.font as tkfont
from pathlib import Path


# ==================== HTTP 方法 ====================

# 支持的 HTTP 方法（顺序对应下拉框显示顺序）
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

# 有请求体的方法（决定 Body 页是否可编辑）
METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}


# ==================== 窗口尺寸 ====================

WINDOW_DEFAULT_SIZE = "1080x680"
WINDOW_MIN_SIZE = (880, 540)


# ==================== 输入控件规格 ====================

PARAMS_ROWS = 5
HEADERS_ROWS = 3

BODY_TEXT_HEIGHT = 12
RESPONSE_TEXT_HEIGHT = 30


# ==================== 调色板（亮色主题）====================

PALETTE_LIGHT = {
    "bg":            "#ffffff",
    "surface":       "#f8fafc",
    "surface_alt":   "#f1f5f9",
    "border":        "#e2e8f0",
    "border_strong": "#cbd5e1",
    "text":          "#0f172a",
    "text_muted":    "#64748b",
    "text_subtle":   "#94a3b8",
    "primary":       "#3b82f6",
    "primary_hover": "#2563eb",
    "primary_active":"#1d4ed8",
    "primary_text":  "#ffffff",
    "success":       "#10b981",
    "warning":       "#f59e0b",
    "error":         "#ef4444",
    "code_bg":       "#0f172a",       # 响应区背景（深色卡片）
    "code_fg":       "#e2e8f0",
    "selection":     "#bfdbfe",
}


# ==================== 调色板（暗色主题）====================

PALETTE_DARK = {
    "bg":            "#0f172a",
    "surface":       "#1e293b",
    "surface_alt":   "#334155",
    "border":        "#334155",
    "border_strong": "#475569",
    "text":          "#f1f5f9",
    "text_muted":    "#cbd5e1",
    "text_subtle":   "#94a3b8",
    "primary":       "#60a5fa",
    "primary_hover": "#3b82f6",
    "primary_active":"#2563eb",
    "primary_text":  "#0f172a",
    "success":       "#34d399",
    "warning":       "#fbbf24",
    "error":         "#f87171",
    "code_bg":       "#020617",       # 更深的暗色卡片
    "code_fg":       "#e2e8f0",
    "selection":     "#1e40af",
}


# ==================== HTTP 方法色（双主题）====================

METHOD_COLORS = {
    "GET":    {"light": "#3b82f6", "dark": "#60a5fa"},  # 蓝
    "POST":   {"light": "#10b981", "dark": "#34d399"},  # 绿
    "PUT":    {"light": "#f59e0b", "dark": "#fbbf24"},  # 橙
    "DELETE": {"light": "#ef4444", "dark": "#f87171"},  # 红
    "PATCH":  {"light": "#8b5cf6", "dark": "#a78bfa"},  # 紫
}


# ==================== 间距 / 圆角 ====================

# 统一间距，让 UI 不挤
PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 16
PAD_XL = 24


# ==================== 配色（旧别名，向后兼容）====================
# 旧代码里可能用到，下面代码已不再引用，但保留别名以防外部引用
COLOR_SUCCESS = PALETTE_LIGHT["success"]
COLOR_ERROR = PALETTE_LIGHT["error"]
COLOR_MUTED = PALETTE_LIGHT["text_muted"]
COLOR_PRIMARY = PALETTE_LIGHT["primary"]


# ==================== 字体 ====================

MONO_FONT_FALLBACKS = [
    "Consolas",
    "Menlo",
    "DejaVu Sans Mono",
    "Courier New",
    "TkFixedFont",
]

UI_FONT_FALLBACKS_WINDOWS = [
    "Microsoft YaHei UI",
    "Segoe UI",
    "Tahoma",
]
UI_FONT_FALLBACKS_MAC = ["Helvetica", "SF Pro Text"]
UI_FONT_FALLBACKS_LINUX = ["Ubuntu", "DejaVu Sans"]


def pick_mono_font() -> tuple:
    """选择系统中可用的等宽字体。"""
    available = set(tkfont.families())
    for name in MONO_FONT_FALLBACKS:
        if name in available:
            return (name, 11)
    return ("TkFixedFont", 11)


def pick_ui_font() -> tuple:
    """选择 UI 默认字体（中文系统优先用系统默认 + 略大尺寸）。"""
    available = set(tkfont.families())
    fallbacks = []
    if sys.platform.startswith("win"):
        fallbacks = UI_FONT_FALLBACKS_WINDOWS
    elif sys.platform == "darwin":
        fallbacks = UI_FONT_FALLBACKS_MAC
    else:
        fallbacks = UI_FONT_FALLBACKS_LINUX
    for name in fallbacks:
        if name in available:
            return (name, 10)
    return ("TkDefaultFont", 10)


# ==================== 示例 / 占位文案 ====================

DEFAULT_PATH = "/users/123"

WELCOME_TEXT = """👋 欢迎使用 intelligent assistant —— api-demo 桌面 GUI

用法三步走：
  1. 点左上角「⚙ 设置」填入 API Key 和 Base URL
     （如果项目根目录有 .env 文件，会自动读取，这一步可跳过）
  2. 选好方法（GET/POST/...）、填写路径，例如 /users/123
  3. 点「🚀 发送请求」，响应会显示在这里

小提示：
  · 点工具栏「📄 使用示例」一键填好示例请求
  · 点右上角「☀」可在 亮色 / 暗色 / 跟随系统 之间切换主题
  · 无需真实 API 也能试玩：
      Base URL: https://jsonplaceholder.typicode.com
      Path:     /todos/1
      API Key:  随便填（公开测试站不校验）
"""


def get_example_request() -> dict:
    """「📄 使用示例」按钮填入的请求内容。"""
    return {
        "method": "GET",
        "path": "/todos/1",
        "params": [("userId", "1")],
        "headers": [],
        "body": "",
    }


HEADERS_NOTE = (
    "提示：Authorization / Content-Type / Accept / User-Agent 由 SDK 自动设置，无需填写"
)


# ==================== 配置路径 ====================

CONFIG_PATH = Path.home() / ".intelligent-assistant-gui.json"

# 兼容旧版：依次尝试这些路径（hub → api-demo → 现在）
CONFIG_PATH_LEGACY = [
    Path.home() / ".hub-gui.json",
    Path.home() / ".api-demo-gui.json",
]

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "",
    "timeout": 30,
    "max_retries": 3,
    "verify_ssl": True,
    "remember_key": False,
    "theme": "light",   # "light" | "dark" | "system"
    # 升级相关
    "last_update_check": 0.0,        # 上次检查时间（Unix timestamp）
    "skipped_version": "",           # 用户点过「跳过此版本」的版本号
    "pending_update_path": "",       # 已下载但未安装的 exe 路径
}


# ==================== 升级相关常量 ====================

# GitHub 仓库
GITHUB_REPO = "carlli666/demo"

# Release 中 asset 的文件名（用户发版时必须用这个名）
UPDATE_ASSET_NAME = "intelligent assistant.exe"

# 自动检查间隔（秒）—— 默认 7 天
UPDATE_CHECK_INTERVAL_DAYS = 7
UPDATE_CHECK_INTERVAL_SECONDS = UPDATE_CHECK_INTERVAL_DAYS * 24 * 3600

# 启动后多久开始后台检查（毫秒）
UPDATE_STARTUP_DELAY_MS = 2000

# 队列轮询间隔（毫秒）
UPDATE_POLL_INTERVAL_MS = 500


# ==================== 异常友好提示（app.py 用）====================

FRIENDLY_ERROR_TEMPLATES = {
    "AuthError": "认证失败：API Key 不对或没有权限（401/403）",
    "NotFoundError": "资源不存在：检查一下路径拼对了吗（404）",
    "RateLimitError": "请求太频繁，等一会儿再试（429）",
    "ServerError": "对方服务器出错，不是你的问题（5xx）",
}