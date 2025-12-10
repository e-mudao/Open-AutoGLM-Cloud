"""Screenshot utilities for capturing Android device screen."""

import base64
import os
import subprocess
import uuid
from dataclasses import dataclass
from io import BytesIO

from PIL import Image


@dataclass
class Screenshot:
    """Represents a captured screenshot."""
    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


def get_screenshot(device_id: str | None = None, timeout: int = 10) -> Screenshot:
    """
    Capture a screenshot from the connected Android device.
    """
    # 使用临时文件路径
    temp_path = f"/tmp/screenshot_{uuid.uuid4()}.png"
    adb_prefix = _get_adb_prefix(device_id)

    try:
        # 1. 执行截图命令
        # screencap -p 会在手机端生成 png 格式
        result = subprocess.run(
            adb_prefix + ["shell", "screencap", "-p", "/sdcard/tmp.png"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 检查是否失败 (敏感页面通常会返回错误或黑屏，但 ADB 响应可能不同)
        output = result.stdout + result.stderr
        if "Status: -1" in output or "Failed" in output:
            return _create_fallback_screenshot(is_sensitive=True)

        # 2. 将图片拉取到本地
        subprocess.run(
            adb_prefix + ["pull", "/sdcard/tmp.png", temp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if not os.path.exists(temp_path):
            return _create_fallback_screenshot(is_sensitive=False)

        # 3. 读取图片信息
        # 优化: 只用 PIL 读取尺寸，直接读取文件二进制数据作为 Base64
        # 避免了原代码中 Image.save() 导致的二次 PNG 压缩，提升速度
        try:
            with Image.open(temp_path) as img:
                width, height = img.size
            
            with open(temp_path, "rb") as f:
                image_bytes = f.read()
                base64_data = base64.b64encode(image_bytes).decode("utf-8")
        except Exception:
            # 如果文件损坏
            return _create_fallback_screenshot(is_sensitive=False)
        finally:
            # 清理本地临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return Screenshot(
            base64_data=base64_data, width=width, height=height, is_sensitive=False
        )

    except Exception as e:
        print(f"Screenshot error: {e}")
        return _create_fallback_screenshot(is_sensitive=False)


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """Create a black fallback image when screenshot fails."""
    # 修改: 匹配您的设备分辨率 720x1604
    default_width, default_height = 720, 1604

    black_img = Image.new("RGB", (default_width, default_height), color="black")
    buffered = BytesIO()
    black_img.save(buffered, format="PNG")
    base64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return Screenshot(
        base64_data=base64_data,
        width=default_width,
        height=default_height,
        is_sensitive=is_sensitive,
    )
