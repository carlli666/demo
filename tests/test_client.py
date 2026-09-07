"""
tests/test_client.py
~~~~~~~~~~~~~~~~~~~

客户端单元测试。

运行命令：
    pytest tests/
"""
import os
import sys

import pytest

# 让测试能找到包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_demo import Client, APIError, AuthError, NotFoundError


@pytest.fixture
def client():
    """创建测试用的客户端"""
    return Client(
        api_key="test_key",
        base_url="https://api.example.com",
        timeout=10,
        max_retries=1,
    )


def test_client_initialization(client):
    """测试客户端初始化"""
    assert client.api_key == "test_key"
    assert client.base_url == "https://api.example.com"
    assert client.timeout == 10


def test_missing_api_key():
    """测试缺少 API_KEY 时报错"""
    # 临时清除环境变量
    os.environ.pop("API_KEY", None)
    with pytest.raises(ValueError, match="API_KEY"):
        Client(base_url="https://api.example.com")


def test_missing_base_url():
    """测试缺少 base_url 时报错"""
    os.environ.pop("API_BASE_URL", None)
    with pytest.raises(ValueError, match="API_BASE_URL"):
        Client(api_key="test_key")


def test_url_building(client):
    """测试 URL 拼接"""
    # 路径不带斜杠
    assert client._build_url("users/123") == "https://api.example.com/users/123"
    # 路径带斜杠
    assert client._build_url("/users/123") == "https://api.example.com/users/123"
    # 完整 URL
    assert client._build_url("https://other.com/path") == "https://other.com/path"


def test_context_manager():
    """测试上下文管理器"""
    with Client(api_key="k", base_url="https://api.example.com") as c:
        assert c is not None
        assert c.api_key == "k"


def test_repr(client):
    """测试字符串表示"""
    r = repr(client)
    assert "https://api.example.com" in r


def test_close(client):
    """测试关闭 Session"""
    client.close()
    # 多次关闭不应报错
    client.close()


# ==================== 认证方式（auth_style）================


def test_default_auth_style_is_api_key(client):
    """默认认证方式应是 api_key（Logicalis 风格）。"""
    assert client.auth_style == "api_key"


def test_invalid_auth_style_rejected():
    """非法 auth_style 应抛 ValueError。"""
    with pytest.raises(ValueError, match="auth_style"):
        Client(
            api_key="k",
            base_url="https://api.example.com",
            auth_style="oauth",  # noqa
        )


def test_request_uses_api_key_header_by_default(monkeypatch):
    """默认情况下请求头应包含 ApiKey，不含 Authorization: Bearer。"""
    import requests

    captured = {}

    def fake_send(self, request, **kwargs):
        captured.update(dict(request.headers))
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b'{"ok": true}'
        return resp

    monkeypatch.setattr(requests.Session, "send", fake_send)

    c = Client(
        api_key="my-uuid-key",
        base_url="https://api.example.com",
        timeout=1,
        max_retries=0,
    )
    c.get("/ping")
    assert captured.get("ApiKey") == "my-uuid-key"
    assert "Authorization" not in captured


def test_request_can_use_bearer_auth(monkeypatch):
    """显式指定 auth_style='bearer' 时用 Authorization: Bearer。"""
    import requests

    captured = {}

    def fake_send(self, request, **kwargs):
        captured.update(dict(request.headers))
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b'{"ok": true}'
        return resp

    monkeypatch.setattr(requests.Session, "send", fake_send)

    c = Client(
        api_key="my-uuid-key",
        base_url="https://api.example.com",
        timeout=1,
        max_retries=0,
        auth_style="bearer",
    )
    c.get("/ping")
    assert captured.get("Authorization") == "Bearer my-uuid-key"
    assert "ApiKey" not in captured
