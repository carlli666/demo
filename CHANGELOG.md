# 更新日志

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [Unreleased]

### ✨ 新增
- **tkinter 桌面 GUI 演示工具**：`api_demo.gui` 子包 + `run_gui.py` 启动脚本
  - 设置对话框（API Key / Base URL / 超时 / 重试 / SSL）
  - 请求构造面板（方法、路径、Params、Headers、Body）
  - 响应展示面板（状态码、耗时、格式化 JSON、错误高亮）
  - 后台线程执行 HTTP，主线程只跑 Tk 界面，避免卡死
  - 新增 `hub` console script（`pip install -e .` 后可命令启动）
- 新增 `build_gui.bat`：一键打包成 `dist/hub.exe`（约 15 MB，自带 reddit 图标）
- 新增 `tests/test_gui_smoke.py`：6 个冒烟测试
- README 新增「🖥️ GUI 桌面版」章节 + 打包说明

### 📝 文档
- README.md：项目结构新增 `api_demo/gui/` 与 `run_gui.py`，新增 GUI 使用说明
- CLAUDE.md：项目结构 / 状态 / 命令同步更新

### 计划中
- 异步客户端支持（asyncio + httpx）
- 自动 Token 刷新机制
- 详细的单元测试覆盖
- API 文档自动生成

---

## [0.1.0] - 2026-09-03

### ✨ 新增
- 初始版本发布
- 基础 `Client` 类，支持 GET/POST/PUT/DELETE/PATCH
- 自动加载 `.env` 配置
- 自动重试机制（429/5xx）
- 连接池优化
- 细粒度异常类型（AuthError / NotFoundError / RateLimitError / ServerError）
- 上下文管理器支持
- 完整的 README 和示例代码

### 📝 文档
- README.md（中文）
- LICENSE（MIT）
- 示例代码（basic_usage.py / advanced_usage.py）
