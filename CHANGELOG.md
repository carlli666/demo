# 更新日志

本项目的所有重要变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

---

## [Unreleased]

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
