"""
make_icon.py
~~~~~~~~~~~~

生成 64x64 的"智能助手"主题 ICO（**BMP-in-ICO 格式**，兼容性最好）。

输出：intelligent_assistant.ico
"""
from __future__ import annotations

import math
import struct
from pathlib import Path


SIZE = 64


# ==================== 像素生成 ====================


def make_rgba_pixels() -> bytes:
    """
    生成 64x64 RGBA 像素（每像素 4 字节），按从上到下、左到右的顺序。
    返回：SIZE * SIZE * 4 字节。
    """
    W = H = SIZE
    cx, cy = W / 2 - 0.5, H / 2 - 0.5

    # 调色板（与 app 主题一致）
    BG_OUTER = (15, 23, 42, 255)        # #0f172a
    BG_INNER = (30, 58, 138, 255)       # #1e3a8a
    RING = (96, 165, 250, 255)          # #60a5fa
    CORE = (147, 197, 253, 255)         # #93c5fd
    DOT = (255, 255, 255, 255)
    SPARK = (96, 165, 250, 255)

    spark_angles = [90, 0, 270, 180]
    spark_radius = 22
    spark_size = 3

    pixels = bytearray()
    for y in range(H):
        for x in range(W):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)

            r, g, b, a = BG_OUTER

            if dist < 24:
                if dist < 14:
                    r, g, b, a = CORE
                else:
                    r, g, b, a = RING

            if dist < 3.5:
                r, g, b, a = DOT

            for ang_deg in spark_angles:
                ang = math.radians(ang_deg)
                sx = math.cos(ang) * spark_radius
                sy = -math.sin(ang) * spark_radius
                sdx = x - (cx + sx)
                sdy = y - (cy + sy)
                sdist = math.sqrt(sdx * sdx + sdy * sdy)
                if sdist < spark_size:
                    r, g, b, a = SPARK
                    break

            pixels.extend([r, g, b, a])

    return bytes(pixels)


# ==================== ICO 编码器（BMP-in-ICO）====================


def make_bmp_in_ico(rgba_pixels: bytes, size: int) -> bytes:
    """
    把 RGBA 像素打包成 BMP-in-ICO 数据块（不含 ICO 头）。
    ICO 里的 BMP 是倒置的（bottom-up），且没有 BMP 文件头（直接从 BITMAPINFOHEADER 开始）。
    """
    # BITMAPINFOHEADER (40 bytes)
    # Windows ICO 用 height = 2 * 实际高度 表示这是带 AND mask 的图标
    bih = struct.pack(
        "<IiiHHIIiiII",
        40,                  # biSize
        size,                # biWidth
        size * 2,            # biHeight = 2*真实高度（表示带 AND mask）
        1,                   # biPlanes
        32,                  # biBitCount
        0,                   # biCompression = BI_RGB
        size * size * 4,     # biSizeImage
        0,                   # biXPelsPerMeter
        0,                   # biYPelsPerMeter
        0,                   # biClrUsed
        0,                   # biClrImportant
    )

    # 像素数据要倒置（bottom-up），且要转 BGRA
    # 每行从底到顶
    row_bytes = size * 4
    pixel_rows = []
    for y in range(size - 1, -1, -1):
        start = y * row_bytes
        row = bytearray(rgba_pixels[start:start + row_bytes])
        # RGBA → BGRA
        for i in range(0, len(row), 4):
            r, g, b, a = row[i], row[i + 1], row[i + 2], row[i + 3]
            row[i] = b
            row[i + 1] = g
            row[i + 2] = r
            row[i + 3] = a
        pixel_rows.append(bytes(row))

    pixel_data = b"".join(pixel_rows)

    # AND mask（全透明 = 0）—— 每个像素 1 bit，每行填充到 32 bit
    # 对 64x64：每行 64 bit = 8 bytes，整除 32 bit，无 padding
    and_row_bytes = (size + 31) // 32 * 4  # = 8 for 64
    and_mask = b"\x00" * (and_row_bytes * size)

    return bih + pixel_data + and_mask


def encode_ico(image_data: bytes, size: int) -> bytes:
    """打包完整 ICO（单个图标，BMP-in-ICO）。"""
    # ICONDIR (6 bytes)
    icondir = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY (16 bytes)
    w = 0 if size == 256 else size
    h = 0 if size == 256 else size
    entry = struct.pack(
        "<BBBBHHII",
        w, h, 0, 0, 1, 32,
        len(image_data),
        22,  # offset = 6 + 16
    )
    return icondir + entry + image_data


# ==================== 主流程 ====================


def main() -> None:
    rgba = make_rgba_pixels()
    bmp_in_ico = make_bmp_in_ico(rgba, SIZE)
    ico = encode_ico(bmp_in_ico, SIZE)

    out = Path(__file__).parent / "intelligent_assistant.ico"
    out.write_bytes(ico)
    print(f"已生成 {out} ({len(ico)} bytes, {SIZE}x{SIZE}, BMP-in-ICO)")


if __name__ == "__main__":
    main()