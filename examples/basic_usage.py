"""
examples/basic_usage.py
~~~~~~~~~~~~~~~~~~~~~~~~

最基础的使用示例：发起一次 GET 请求获取用户信息。

运行前请确保：
1. 已在项目根目录创建 .env 文件
2. .env 文件中设置了 API_KEY 和 API_BASE_URL

运行命令：
    python examples/basic_usage.py
"""
import os
import sys

# 让脚本能找到 api_demo 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_demo import Client, APIError, AuthError, NotFoundError


def main():
    """演示基本的 GET 请求"""
    print("=" * 60)
    print("示例 1：使用上下文管理器（推荐）")
    print("=" * 60)

    # 方式一：使用 with 语句（推荐，自动关闭连接）
    try:
        with Client() as client:
            # 调用接口（请将 /users/123 替换为你文档中的真实路径）
            result = client.get("/users/123")
            print(f"成功：{result}")
    except AuthError as e:
        print(f"认证失败：{e}")
    except NotFoundError as e:
        print(f"用户不存在：{e}")
    except APIError as e:
        print(f"API 错误：{e}")

    print()
    print("=" * 60)
    print("示例 2：手动管理客户端")
    print("=" * 60)

    # 方式二：手动创建和关闭
    client = Client()
    try:
        result = client.get("/users", params={"page": 1, "size": 10})
        print(f"用户列表：{result}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
