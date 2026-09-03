"""
api_demo.gui.constants
~~~~~~~~~~~~~~~~~~~~~~~

GUI 模块用到的常量、文案、配色、示例数据。

把所有「文字 / 颜色 / 字号 / 默认值」集中在这里，方便后续修改和翻译。
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

# 主窗口默认尺寸 / 最小尺寸
WINDOW_DEFAULT_SIZE = "1000x640"
WINDOW_MIN_SIZE = (820, 520)


# ==================== 输入控件规格 ====================

# Params / Headers 的固定行数（小白友好：不会动态增删）
PARAMS_ROWS = 5
HEADERS_ROWS = 3

# Body 文本框高度（行）
BODY_TEXT_HEIGHT = 10

# 响应文本框高度（行）
RESPONSE_TEXT_HEIGHT = 30


# ==================== 配色 ====================

# 状态色（label 前景）
COLOR_SUCCESS = "#27ae60"  # 绿色：成功
COLOR_ERROR = "#c0392b"  # 红色：错误
COLOR_MUTED = "#7f8c8d"  # 灰：次要说明
COLOR_PRIMARY = "#2c3e50"  # 深蓝：主文字


# ==================== 字体 ====================

# 跨平台等宽字体 fallback
MONO_FONT_FALLBACKS = [
    "Consolas",
    "Menlo",
    "DejaVu Sans Mono",
    "Courier New",
    "TkFixedFont",
]


def pick_mono_font() -> tuple:
    """
    选择系统中可用的等宽字体。

    :return: (family, size) 元组
    """
    available = set(tkfont.families())
    for name in MONO_FONT_FALLBACKS:
        if name in available:
            return (name, 11)
    # 兜底：TkFixedFont 一定可用
    return ("TkFixedFont", 11)


def pick_ui_font() -> tuple:
    """
    选择 UI 默认字体（中文系统优先用系统默认 + 略大尺寸）。

    :return: (family, size) 元组
    """
    if sys.platform.startswith("win"):
        return ("Microsoft YaHei UI", 10)
    if sys.platform == "darwin":
        return ("Helvetica", 13)
    return ("TkDefaultFont", 11)


# ==================== 示例 / 占位文案 ====================

# 启动时 Path 框预填内容
DEFAULT_PATH = "/users/123"

# 响应区启动显示的欢迎语
WELCOME_TEXT = """👋 欢迎使用 api-demo GUI 演示工具

用法三步走：
  1. 点左上角「⚙ 设置」填入 API Key 和 Base URL
     （如果项目根目录有 .env 文件，会自动读取，这一步可跳过）
  2. 选好方法（GET/POST/...）、填写路径，例如 /users/123
  3. 点「🚀 发送请求」，响应会显示在这里

小提示：点「📄 使用示例」可以一键填好一个示例请求。

没有真实 API 也能试玩：
  Base URL: https://jsonplaceholder.typicode.com
  Path:     /todos/1
  API Key:  随便填几个字符（该站不校验）
"""


def get_example_request() -> dict:
    """
    返回「📄 使用示例」按钮填入的请求内容。

    :return: dict，包含 method / path / params / headers / body
    """
    return {
        "method": "GET",
        "path": "/todos/1",
        "params": [("userId", "1")],  # 列表 of (key, value)，空 key 会被忽略
        "headers": [],
        "body": "",
    }


# ==================== Headers 提示 ====================

# Headers 页顶部的灰色提示（说明 4 个 SDK 自动头改不了）
HEADERS_NOTE = (
    "提示：Authorization / Content-Type / Accept / User-Agent 由 SDK 自动设置，无需填写"
)


# ==================== 配置路径 ====================

# 用户配置文件位置：~/.hub-gui.json
CONFIG_PATH = Path.home() / ".hub-gui.json"

# 兼容旧版：优先读新路径，文件不存在时尝试旧路径 ~/.api-demo-gui.json
CONFIG_PATH_LEGACY = Path.home() / ".api-demo-gui.json"


# ==================== 设置对话框默认值 ====================

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "",
    "timeout": 30,
    "max_retries": 3,
    "verify_ssl": True,
    "remember_key": False,
}


# ==================== 异常友好提示 ====================

# 在 app.py 里实际使用时会导入具体异常类
FRIENDLY_ERROR_TEMPLATES = {
    "AuthError": "认证失败：API Key 不对或没有权限（401/403）",
    "NotFoundError": "资源不存在：检查一下路径拼对了吗（404）",
    "RateLimitError": "请求太频繁，等一会儿再试（429）",
    "ServerError": "对方服务器出错，不是你的问题（5xx）",
}