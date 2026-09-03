"""
api_demo.exceptions
~~~~~~~~~~~~~~~~~~~

对外暴露的异常类型。
"""
from .client import (
    APIError,
    AuthError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

__all__ = [
    "APIError",
    "AuthError",
    "NotFoundError",
    "RateLimitError",
    "ServerError",
]
