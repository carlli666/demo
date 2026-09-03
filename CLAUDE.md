# CLAUDE.md - api-demo 项目说明

> 本文件供 Claude Code 读取，了解项目背景和当前状态。

## 项目概述

这是一个**对接公司平台 RESTful API 的 Python SDK**，当前处于 **0.1.0 初始版本**。

## 技术栈

- **语言**：Python 3.14.4（要求 3.9+）
- **核心依赖**：requests, python-dotenv
- **开发依赖**：pytest
- **打包**：setuptools + pyproject.toml

## 项目结构

```
D:\projects\demo\
├── api_demo/        核心代码
│   ├── client.py    Client 类（带重试、错误处理、连接池）
│   ├── exceptions.py
│   └── gui/         tkinter 桌面 GUI（演示用）
├── examples/        使用示例（基础 + 高级）
├── tests/           pytest 单元测试（13 个用例）
├── docs/            文档（对话记录、截图等）
├── run_gui.py       GUI 启动脚本
├── venv/            虚拟环境（不入库）
└── 配置文件          README, LICENSE, .gitignore 等
```

## 当前状态

✅ **已完成**：
- 项目结构搭建
- Client 类实现（带重试、错误处理、连接池）
- 13 个单元测试全部通过（原 7 + GUI 冒烟 6）
- 完整开源文档（README、LICENSE、CHANGELOG）
- **tkinter GUI 桌面演示工具**（无新增运行时依赖）
- 上传到 GitHub：https://github.com/callli666/demo

🚧 **待完善**：
- 真实业务接口方法（待用户提供 API 文档细节）
- README 中的个人信息（用户名、邮箱）
- GitHub Topics 标签
- GUI 截图（需手动截，路径 `docs/images/gui-screenshot.png`）

## 开发约定

- Python 代码用 `black` 格式化（line-length=100）
- 类型提示完整
- 错误处理细粒度（专用异常类）
- 每个公开方法都要有 docstring
- 测试放在 tests/ 目录

## 常用命令

```bash
# 激活虚拟环境
cd D:\projects\demo
.\venv\Scripts\Activate.ps1

# 跑测试
pytest tests/

# 跑示例
python examples/basic_usage.py

# 启动 GUI 桌面版
python run_gui.py

# 提交代码
git add .
git commit -m "描述"
git push
```

## 用户信息

- GitHub 用户名：carlli666
- 邮箱：lhe6183@gmail.com
- 用户水平：编程小白，需要详细指导

## 下次对话可以从这里继续

如果用户回到这个项目，可以问：
- "我们之前搭好的 api-demo 项目，怎么继续开发？"
- "帮我加一个获取用户信息的接口方法"
- "怎么把这个项目发布到 PyPI？"
