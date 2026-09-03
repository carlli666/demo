"""
examples/advanced_usage.py
~~~~~~~~~~~~~~~~~~~~~~~~~~

高级用法示例：POST/PUT/DELETE、错误处理、自定义配置。

运行命令：
    python examples/advanced_usage.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api_demo import Client, APIError, AuthError, RateLimitError


def example_post():
    """演示 POST 创建资源"""
    print("=" * 60)
    print("示例 1：POST 创建数据")
    print("=" * 60)

    with Client() as client:
        try:
            new_user = client.post(
                "/users",
                json={
                    "name": "张三",
                    "email": "zhangsan@example.com",
                    "role": "developer",
                },
            )
            print(f"创建成功：{new_user}")
            return new_user
        except APIError as e:
            print(f"创建失败：{e}")
            return None


def example_put(user_id: str):
    """演示 PUT 更新资源"""
    print()
    print("=" * 60)
    print(f"示例 2：PUT 更新用户 {user_id}")
    print("=" * 60)

    with Client() as client:
        try:
            updated = client.put(
                f"/users/{user_id}",
                json={"name": "李四"},
            )
            print(f"更新成功：{updated}")
        except APIError as e:
            print(f"更新失败：{e}")


def example_delete(user_id: str):
    """演示 DELETE 删除资源"""
    print()
    print("=" * 60)
    print(f"示例 3：DELETE 删除用户 {user_id}")
    print("=" * 60)

    with Client() as client:
        try:
            result = client.delete(f"/users/{user_id}")
            print(f"删除成功：{result}")
        except APIError as e:
            print(f"删除失败：{e}")


def example_custom_config():
    """演示自定义超时和重试配置"""
    print()
    print("=" * 60)
    print("示例 4：自定义配置")
    print("=" * 60)

    # 自定义超时 60 秒，最多重试 5 次
    client = Client(
        timeout=60,
        max_retries=5,
        backoff_factor=1.0,  # 重试间隔更长
    )

    try:
        result = client.get("/health")
        print(f"健康检查：{result}")
    except APIError as e:
        print(f"检查失败：{e}")
    finally:
        client.close()


def example_error_handling():
    """演示如何处理各种错误"""
    print()
    print("=" * 60)
    print("示例 5：详细的错误处理")
    print("=" * 60)

    with Client() as client:
        try:
            # 模拟一个可能失败的操作
            client.get("/some-endpoint")
        except AuthError as e:
            print(f"[401/403] 请检查 API_KEY 是否正确")
            print(f"  详情：{e}")
        except RateLimitError as e:
            print(f"[429] 请求过快，请稍后重试")
            print(f"  详情：{e}")
        except APIError as e:
            print(f"[其它错误] 状态码：{e.status_code}")
            print(f"  详情：{e}")
            print(f"  响应：{e.response}")


if __name__ == "__main__":
    # 按需执行示例
    new_user = example_post()
    if new_user and isinstance(new_user, dict) and "id" in new_user:
        example_put(new_user["id"])
        example_delete(new_user["id"])

    example_custom_config()
    example_error_handling()
