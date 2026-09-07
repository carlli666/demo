"""
api_demo.client
~~~~~~~~~~~~~~~

对接公司平台 API 的核心客户端模块。

使用示例：

    from api_demo import Client

    client = Client(api_key="your_key")
    result = client.get("/users/123")
    print(result)
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ==================== 异常定义 ====================

class APIError(Exception):
    """API 调用基础异常"""
    def __init__(self, message: str, status_code: int = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthError(APIError):
    """认证失败异常（401、403）"""


class NotFoundError(APIError):
    """资源不存在异常（404）"""


class RateLimitError(APIError):
    """请求频率超限异常（429）"""


class ServerError(APIError):
    """服务器错误异常（5xx）"""


# ==================== 主客户端 ====================

class Client:
    """
    对接公司平台的同步客户端。

    支持自动重试、连接池、错误处理和上下文管理器。

    :param api_key: API 密钥，未传入则从环境变量 API_KEY 读取
    :param base_url: API 基础地址，例如 https://api.example.com
    :param timeout: 单次请求超时时间（秒），默认 30
    :param max_retries: 失败重试次数，默认 3
    :param backoff_factor: 重试退避因子，默认 0.5
    :param verify_ssl: 是否校验 SSL 证书，默认 True
    :param auth_style: 认证方式，可选 ``"api_key"``（默认，发送 ``ApiKey: <key>`` 头）
        或 ``"bearer"``（发送 ``Authorization: Bearer <key>`` 头）
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF = 0.5

    # 支持的认证方式
    AUTH_STYLES = ("api_key", "bearer")

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF,
        verify_ssl: bool = True,
        auth_style: str = "api_key",
    ):
        import os
        from dotenv import load_dotenv

        load_dotenv()  # 自动加载 .env 文件

        if auth_style not in self.AUTH_STYLES:
            raise ValueError(
                f"auth_style 必须是 {self.AUTH_STYLES} 之一，收到：{auth_style!r}"
            )

        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = (base_url or os.getenv("API_BASE_URL", "")).rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.auth_style = auth_style

        if not self.api_key:
            raise ValueError(
                "未找到 API_KEY，请通过参数传入或设置环境变量 API_KEY"
            )
        if not self.base_url:
            raise ValueError(
                "未找到 API_BASE_URL，请通过参数传入或设置环境变量 API_BASE_URL"
            )

        # 创建带重试机制的 Session
        self.session = self._create_session(max_retries, backoff_factor)

    # ---------- 公共方法：HTTP 动词封装 ----------

    def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> Any:
        """发送 GET 请求"""
        return self._request("GET", path, params=params, **kwargs)

    def post(self, path: str, json: Optional[Dict] = None, data: Any = None, **kwargs) -> Any:
        """发送 POST 请求"""
        return self._request("POST", path, json=json, data=data, **kwargs)

    def put(self, path: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """发送 PUT 请求"""
        return self._request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs) -> Any:
        """发送 DELETE 请求"""
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """发送 PATCH 请求"""
        return self._request("PATCH", path, json=json, **kwargs)

    # ---------- 上下文管理器 ----------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """关闭 Session，释放连接"""
        if self.session:
            self.session.close()
            logger.debug("API Client Session 已关闭")

    # ---------- 私有方法 ----------

    def _create_session(self, max_retries: int, backoff_factor: float) -> requests.Session:
        """创建带自动重试的 Session"""
        session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _build_url(self, path: str) -> str:
        """拼接完整 URL"""
        if path.startswith(("http://", "https://")):
            return path
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Any = None,
        **kwargs,
    ) -> Any:
        """
        底层请求方法。

        :param method: HTTP 方法
        :param path: 接口路径
        :param params: URL 查询参数
        :param json: JSON 请求体
        :param data: 原始请求体
        :return: 解析后的 JSON 响应数据
        :raises APIError: 请求失败时抛出
        """
        url = self._build_url(path)

        headers = kwargs.pop("headers", {})
        # 认证头：默认使用 Logicalis 风格的 ApiKey 头，可选 Bearer 兼容老服务
        if self.auth_style == "api_key":
            headers["ApiKey"] = self.api_key
        else:  # bearer
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "api-demo-python/0.1.0",
        })

        start_time = time.time()
        try:
            logger.debug(f"→ {method} {url}")
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                data=data,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs,
            )
        except requests.exceptions.Timeout:
            raise APIError(f"请求超时（>{self.timeout}s）: {method} {url}")
        except requests.exceptions.ConnectionError as e:
            raise APIError(f"网络连接失败: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"请求异常: {str(e)}")

        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"← {response.status_code} {method} {url} ({elapsed:.0f}ms)")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Any:
        """统一处理响应，转换为对应异常或返回数据"""
        status = response.status_code

        # 尝试解析响应体
        try:
            payload = response.json() if response.content else {}
        except (json.JSONDecodeError, ValueError):
            payload = {"raw": response.text}

        # 根据状态码分类处理
        if 200 <= status < 300:
            return payload

        if status == 401 or status == 403:
            raise AuthError(
                f"认证失败 [{status}]: {payload}",
                status_code=status,
                response=payload,
            )
        if status == 404:
            raise NotFoundError(
                f"资源不存在 [404]: {payload}",
                status_code=status,
                response=payload,
            )
        if status == 429:
            raise RateLimitError(
                f"请求频率超限 [429]: {payload}",
                status_code=status,
                response=payload,
            )
        if 500 <= status < 600:
            raise ServerError(
                f"服务器错误 [{status}]: {payload}",
                status_code=status,
                response=payload,
            )

        raise APIError(
            f"请求失败 [{status}]: {payload}",
            status_code=status,
            response=payload,
        )

    def __repr__(self) -> str:
        return f"<Client base_url={self.base_url!r}>"
