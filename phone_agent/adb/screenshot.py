"""Screenshot utilities for capturing Android device screen."""

import base64
import os
import subprocess
import uuid
from dataclasses import dataclass
from io import BytesIO
import tempfile # [新增] 用于更安全的跨平台本地临时文件处理

from PIL import Image


@dataclass
class Screenshot:
    """Represents a captured screenshot."""
    base64_data: str
    width: int
    height: int
    is_sensitive: bool = False


# [新增] 默认的 Fallback 分辨率。
# TODO: 在实际生产环境中，最好在 Agent 初始化时获取一次设备的真实分辨率并存储起来传递给此模块，
# 而不是依赖硬编码的默认值。
DEFAULT_FALLBACK_SIZE = (720, 1604)


def get_screenshot(device_id: str | None = None, timeout: int = 12) -> Screenshot:
    """
    Capture a screenshot from the connected Android device.

    Args:
        device_id: Optional ADB device ID.
        timeout: Timeout in seconds for ADB commands. Increased to 12s for slower devices.

    Returns:
        Screenshot object. Returns a black fallback image on failure.
    """
    # 生成唯一的 ID，避免多进程或短时间内连续截图导致文件名冲突
    unique_id = uuid.uuid4().hex[:8]

    # [优化 1] 使用 tempfile 模块获取本地临时目录，跨平台兼容性更好 (Windows/Linux/macOS)
    local_temp_dir = tempfile.gettempdir()
    local_temp_path = os.path.join(local_temp_dir, f"sc_{unique_id}.png")

    # [优化 2] 远程文件名也使用唯一 ID，避免冲突。
    # 使用 /data/local/tmp/ 目录通常比 /sdcard/ 更规范，权限也更明确。
    remote_temp_path = f"/data/local/tmp/sc_{unique_id}.png"

    adb_prefix = _get_adb_prefix(device_id)

    try:
        # 1. 执行截图命令并保存到手机端临时位置
        # capture_output=True 会捕获 stdout/stderr，对于检测敏感页面失败很有用
        result = subprocess.run(
            adb_prefix + ["shell", "screencap", "-p", remote_temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 检查是否失败 (敏感页面通常会返回错误输出)
        # 某些设备/系统版本在受保护页面截图时，stderr 会包含 "ERROR: capture failed" 或类似信息
        output = result.stdout + result.stderr
        if result.returncode != 0 or "failed" in output.lower():
            # print(f"Screenshot capture failed (likely sensitive output): {output}") # 可选调试日志
            return _create_fallback_screenshot(is_sensitive=True)

        # 2. 将图片拉取到本地
        pull_result = subprocess.run(
            adb_prefix + ["pull", remote_temp_path, local_temp_path],
            capture_output=True, # 捕获输出避免刷屏
            timeout=timeout, # 拉取大文件可能需要时间
        )

        if pull_result.returncode != 0 or not os.path.exists(local_temp_path):
             # print(f"Failed to pull screenshot: {pull_result.stderr.decode()}")
             return _create_fallback_screenshot(is_sensitive=False)

        # 3. 读取图片信息
        # 原代码的优化非常好：只用 PIL 读尺寸，用原生 IO 读数据转换为 Base64。保持不变。
        try:
            with Image.open(local_temp_path) as img:
                width, height = img.size

            with open(local_temp_path, "rb") as f:
                image_bytes = f.read()
                base64_data = base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            print(f"Error reading screenshot file: {e}")
            # 如果文件损坏或读取失败
            return _create_fallback_screenshot(is_sensitive=False)

        return Screenshot(
            base64_data=base64_data, width=width, height=height, is_sensitive=False
        )

    except subprocess.TimeoutExpired:
        print("Screenshot timed out.")
        return _create_fallback_screenshot(is_sensitive=False)
    except Exception as e:
        print(f"Unexpected screenshot error: {e}")
        return _create_fallback_screenshot(is_sensitive=False)
    finally:
        # [优化 3] 清理工作：确保删除本地和远程的临时文件
        if os.path.exists(local_temp_path):
            try:
                os.remove(local_temp_path)
            except Exception:
                pass # 忽略清理本地文件时的错误

        # 清理远程文件 (尝试执行，不保证成功，设置较短超时)
        try:
             subprocess.run(
                 adb_prefix + ["shell", "rm", remote_temp_path],
                 capture_output=True,
                 timeout=2
             )
        except Exception:
             pass # 忽略清理远程文件时的错误 (例如设备断开)


def _get_adb_prefix(device_id: str | None) -> list[str]:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]


def _create_fallback_screenshot(is_sensitive: bool) -> Screenshot:
    """Create a black fallback image when screenshot fails."""
    # [优化 4] 使用顶部定义的常量，并添加注释说明风险。
    # 风险提示：如果此分辨率与实际设备差距过大，VLM 基于此黑图输出的坐标可能是错误的。
    default_width, default_height = DEFAULT_FALLBACK_SIZE

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