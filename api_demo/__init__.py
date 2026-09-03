"""
api_demo
~~~~~~~~

对接公司平台 API 的 Python SDK。

使用示例：

    from api_demo import Client, APIError

    try:
        with Client() as client:
            data = client.get("/users/123")
            print(data)
    except APIError as e:
        print(f"错误: {e}")
"""
from .client import (
    Client,
    APIError,
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

__version__ = "0.1.0"
__author__ = "carlli666"
__license__ = "MIT"

__all__ = [
    "Client",
    "APIError",
    "AuthError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
    "__version__",
]
