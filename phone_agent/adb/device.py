"""Device control utilities for Android automation."""

import subprocess
import time
import random
from phone_agent.config.apps import APP_PACKAGES

# --- 分辨率配置 ---
# 仅用于边界检查，防止抖动出界
DEVICE_WIDTH = 720
DEVICE_HEIGHT = 1604

def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]

def get_current_app(device_id: str | None = None) -> str:
    """Get the currently focused app name."""
    adb_prefix = _get_adb_prefix(device_id)
    try:
        result = subprocess.run(
            adb_prefix + ["shell", "dumpsys", "window"], 
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                for app_name, package in APP_PACKAGES.items():
                    if package in line:
                        return app_name
    except Exception:
        pass
    return "System Home"

def tap(x: int | str | list, y: int | None = None, device_id: str | None = None, delay: float = 1.0) -> None:
    """
    Tap at the specified coordinates.
    Input coordinates are expected to be REAL PIXEL COORDINATES (already scaled by upper layers).
    """
    
    # 1. 解析坐标输入 (处理 list, str 或 int)
    final_x, final_y = 0, 0
    try:
        if isinstance(x, str) and "[" in x:
            import ast
            parsed = ast.literal_eval(x)
            final_x, final_y = int(parsed[0]), int(parsed[1])
        elif isinstance(x, (list, tuple)):
             final_x, final_y = int(x[0]), int(x[1])
        else:
            final_x, final_y = int(x), int(y)
    except Exception as e:
        print(f"⚠️ 坐标解析失败: {x}, {y} -> {e}")
        return

    # 2. 添加随机抖动 (Jitter)
    # 模拟人类手指，防止在同一个死像素点无效点击
    jitter_x = random.randint(-5, 5)
    jitter_y = random.randint(-5, 5)
    
    # 3. 边界检查 (确保不点出屏幕外)
    click_x = max(0, min(final_x + jitter_x, DEVICE_WIDTH))
    click_y = max(0, min(final_y + jitter_y, DEVICE_HEIGHT))
    
    print(f"👉 Tap: 传入[{final_x},{final_y}] -> 抖动后[{click_x},{click_y}]")

    # 4. 执行点击
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(click_x), str(click_y)], 
        capture_output=True
    )
    time.sleep(delay)

def double_tap(x: int | list, y: int | None = None, device_id: str | None = None, delay: float = 1.0) -> None:
    """Double tap at specific coordinates."""
    # 解析坐标
    if isinstance(x, (list, tuple)):
        final_x, final_y = int(x[0]), int(x[1])
    else:
        final_x, final_y = int(x), int(y)

    adb_prefix = _get_adb_prefix(device_id)
    cmd = ["shell", "input", "tap", str(final_x), str(final_y)]
    
    # 双击
    subprocess.run(adb_prefix + cmd, capture_output=True)
    time.sleep(0.1)
    subprocess.run(adb_prefix + cmd, capture_output=True)
    time.sleep(delay)

def long_press(x: int | list, y: int | None = None, duration_ms: int = 1000, device_id: str | None = None, delay: float = 1.0) -> None:
    """Long press."""
    if isinstance(x, (list, tuple)):
        final_x, final_y = int(x[0]), int(x[1])
    else:
        final_x, final_y = int(x), int(y)

    adb_prefix = _get_adb_prefix(device_id)
    # Android 长按通过 swipe 同一点实现
    subprocess.run(
        adb_prefix + ["shell", "input", "swipe", str(final_x), str(final_y), str(final_x), str(final_y), str(duration_ms)],
        capture_output=True,
    )
    time.sleep(delay)

def swipe(start_x: int | list, start_y: int | None, end_x: int | None = None, end_y: int | None = None, duration_ms: int | None = None, device_id: str | None = None, delay: float = 1.0) -> None:
    """Swipe between coordinates."""
    
    # 解析起始坐标
    if isinstance(start_x, (list, tuple)):
        s_x, s_y = int(start_x[0]), int(start_x[1])
        # 如果 end_x 是 list (通常不会这样调用，但为了兼容)
        if isinstance(start_y, (list, tuple)):
            e_x, e_y = int(start_y[0]), int(start_y[1])
        else:
            e_x, e_y = int(end_x), int(end_y)
    else:
        s_x, s_y = int(start_x), int(start_y)
        e_x, e_y = int(end_x), int(end_y)
    
    adb_prefix = _get_adb_prefix(device_id)

    if duration_ms is None:
        # 简单计算滑动时间
        dist_sq = (s_x - e_x) ** 2 + (s_y - e_y) ** 2
        duration_ms = int(dist_sq / 1000)
        duration_ms = max(500, min(duration_ms, 2000))

    subprocess.run(
        adb_prefix + ["shell", "input", "swipe", str(s_x), str(s_y), str(e_x), str(e_y), str(duration_ms)],
        capture_output=True,
    )
    time.sleep(delay)

def back(device_id: str | None = None, delay: float = 1.0) -> None:
    """Press back button."""
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(adb_prefix + ["shell", "input", "keyevent", "4"], capture_output=True)
    time.sleep(delay)

def home(device_id: str | None = None, delay: float = 1.0) -> None:
    """Press home button."""
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(adb_prefix + ["shell", "input", "keyevent", "KEYCODE_HOME"], capture_output=True)
    time.sleep(delay)

def launch_app(app_name: str, device_id: str | None = None, delay: float = 1.0) -> bool:
    """Launch an app by name."""
    if app_name not in APP_PACKAGES:
        return False

    adb_prefix = _get_adb_prefix(device_id)
    package = APP_PACKAGES[app_name]

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "monkey",
            "-p",
            package,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ],
        capture_output=True,
    )
    time.sleep(delay)
    return True
