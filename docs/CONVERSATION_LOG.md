# 开发对话记录（项目搭建全过程）

> 本文档记录了 api-demo 项目从零搭建的全过程，方便日后回顾。

---

## 📋 对话概览

**开始时间**：2026-09-03  
**项目路径**：`D:\projects\demo`  
**目标**：搭建一个对接公司平台 RESTful API 的 Python 开源 SDK

---

## 🛠️ 环境准备阶段

### 1. 安装的核心工具

| 工具 | 版本 | 作用 |
|------|------|------|
| Python | 3.14.4 | 开发语言 |
| Git | 2.55.0 | 版本控制 |
| VS Code | - | 代码编辑器 |
| venv | - | Python 虚拟环境 |

### 2. 创建的虚拟环境

```bash
# 创建路径
D:\projects\demo\venv

# 激活命令（PowerShell）
.\venv\Scripts\Activate.ps1

# 激活成功的标志：路径前出现 (venv)
# 例如：(venv) PS D:\projects\demo>
```

### 3. 安装的 Python 包

```
requests          2.34.2    HTTP 请求核心库
python-dotenv     1.2.3     读取 .env 配置
urllib3           2.7.0     requests 依赖
certifi           2026.7.22 SSL 证书
charset-normalizer 3.5.1    字符编码
idna              3.19      域名处理
pip               26.0.1    包管理器
pytest            9.1.1     测试框架（dev 依赖）
```

---

## 📁 项目结构搭建

### 创建的目录

```
D:\projects\demo\
├── api_demo/              核心 Python 包
│   ├── __init__.py        包入口
│   ├── client.py          Client 主类（约 250 行）
│   └── exceptions.py      异常定义
├── examples/              使用示例
│   ├── __init__.py
│   ├── basic_usage.py     基础示例
│   └── advanced_usage.py  高级示例
├── tests/                 单元测试
│   ├── __init__.py
│   └── test_client.py     7 个测试用例
├── docs/                  文档
│   └── CONVERSATION_LOG.md (本文件)
├── venv/                  虚拟环境
├── .env.example           环境变量模板
├── .gitignore             Git 忽略规则
├── LICENSE                MIT 开源协议
├── README.md              项目说明文档
├── CHANGELOG.md           更新日志
├── pyproject.toml         项目元数据
└── requirements.txt       依赖清单
```

---

## 💻 核心代码（client.py 要点）

### Client 类的特性

```python
class Client:
    # 核心方法
    def __init__(self, api_key=None, base_url=None, timeout=30, 
                 max_retries=3, backoff_factor=0.5, verify_ssl=True)
    
    def get(self, path, params=None)        # GET 请求
    def post(self, path, json=None)         # POST 请求
    def put(self, path, json=None)          # PUT 请求
    def delete(self, path)                  # DELETE 请求
    def patch(self, path, json=None)        # PATCH 请求
    
    def __enter__ / __exit__                # 上下文管理器
    def close()                             # 关闭连接
```

### 异常类型

```python
APIError          # 基础异常
├── AuthError     # 401/403 认证失败
├── NotFoundError # 404 资源不存在
├── RateLimitError # 429 频率限制
└── ServerError   # 5xx 服务器错误
```

### 自动重试机制

- 默认重试 3 次
- 触发重试的状态码：429, 500, 502, 503, 504
- 退避因子：0.5（指数退避）

---

## ✅ 测试结果

```
============================== 7 passed in 0.09s ==============================
tests/test_client.py::test_client_initialization PASSED
tests/test_client.py::test_missing_api_key PASSED
tests/test_client.py::test_missing_base_url PASSED
tests/test_client.py::test_url_building PASSED
tests/test_client.py::test_context_manager PASSED
tests/test_client.py::test_repr PASSED
tests/test_client.py::test_close PASSED
```

---

## 🚀 GitHub 上传记录

### Git 配置

```bash
user.name = callli666
user.email = lhe6183@gmail.com
```

### 关键命令

```bash
# 1. 初始化
git init

# 2. 添加所有文件（.env 和 venv 被 .gitignore 自动排除）
git add .

# 3. 提交
git commit -m "feat: 初始化 api-demo 项目"

# 4. 关联远程仓库
git remote add origin https://github.com/callli666/demo.git

# 5. 推送到 GitHub
git branch -M main
git push -u origin main
```

### 最终结果

```
远程仓库：https://github.com/callli666/demo
默认分支：main
提交记录：35e3950 feat: 初始化 api-demo 项目
```

---

## 📝 后续待办事项

### 必做

- [ ] 在 GitHub 仓库页面添加 Topics 标签：`python` `api` `sdk` `rest-api`
- [ ] 修改 README.md 中的占位信息（用户名、邮箱等）
- [ ] 根据真实 API 文档，添加业务方法到 client.py
- [ ] 完善单元测试，覆盖实际业务场景

### 选做

- [ ] 异步客户端（基于 httpx）
- [ ] 自动 Token 刷新机制
- [ ] GitHub Actions CI/CD
- [ ] 发布到 PyPI（让用户能 `pip install`）
- [ ] 写英文版 README（吸引国外用户）

---

## 🔧 常用命令速查

### 日常开发

```bash
# 激活虚拟环境（每次开新终端都要）
cd D:\projects\demo
.\venv\Scripts\Activate.ps1

# 跑测试
pytest tests/

# 跑示例
python examples/basic_usage.py

# 查看 Git 状态
git status

# 提交并推送
git add .
git commit -m "描述你的改动"
git push
```

### 排查问题

```bash
# 查看已安装的包
pip list

# 重新生成 requirements.txt
pip freeze > requirements.txt

# 查看提交历史
git log --oneline

# 查看具体改了什么
git diff
```

---

## 💡 关键经验教训

1. **虚拟环境必备**：避免库版本冲突，每个项目独立
2. **`.env` 永远不入库**：用 `.env.example` 提供模板
3. **API 文档要看清**：认证方式、限流、错误码都要明确
4. **错误处理要细**：分类异常（Auth/NotFound/RateLimit/Server）
5. **测试覆盖核心**：保证代码质量，便于重构
6. **README 是门面**：决定别人会不会用你的项目

---

> 最后更新：2026-09-03  
> 整理人：Claude Code
