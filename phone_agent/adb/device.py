"""Device control utilities for Android automation."""

import subprocess
import time
import random
import re
from phone_agent.config.apps import APP_PACKAGES

# --- Dynamic Resolution Detection ---
def _get_device_resolution(device_id: str | None = None) -> tuple[int, int]:
    cmd = ["adb"]
    if device_id: cmd.extend(["-s", device_id])
    cmd.extend(["shell", "wm", "size"])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        match = re.search(r"(\d+)x(\d+)", res.stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
    except:
        pass
    return 1080, 2400

DEVICE_WIDTH, DEVICE_HEIGHT = _get_device_resolution()
print(f"📱 Detected Resolution: {DEVICE_WIDTH}x{DEVICE_HEIGHT}")

def _get_adb_prefix(device_id: str | None) -> list:
    if device_id: return ["adb", "-s", device_id]
    return ["adb"]

def get_current_app(device_id: str | None = None) -> str:
    adb_prefix = _get_adb_prefix(device_id)
    try:
        result = subprocess.run(
            adb_prefix + ["shell", "dumpsys", "window"], 
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                for app_name, package in APP_PACKAGES.items():
                    if package in line: return app_name
    except: pass
    return "System Home"

def tap(x: int | str | list, y: int | None = None, device_id: str | None = None, delay: float = 1.0) -> None:
    """
    Tap with Jitter. 
    Coordinates must be PIXELS (integers).
    """
    final_x, final_y = 0, 0
    try:
        # Handle various input types just in case
        if isinstance(x, (list, tuple)): final_x, final_y = int(x[0]), int(x[1])
        else: final_x, final_y = int(x), int(y)
    except Exception as e:
        print(f"⚠️ Tap Error: {e}")
        return

    # Add Jitter (Simulate human touch)
    jitter_range = 5
    jitter_x = random.randint(-jitter_range, jitter_range)
    jitter_y = random.randint(-jitter_range, jitter_range)
    
    # Boundary Check
    click_x = max(0, min(final_x + jitter_x, DEVICE_WIDTH))
    click_y = max(0, min(final_y + jitter_y, DEVICE_HEIGHT))
    
    print(f"👉 Tap: [{final_x},{final_y}] -> Jittered: [{click_x},{click_y}]")

    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(
        adb_prefix + ["shell", "input", "tap", str(click_x), str(click_y)], 
        capture_output=True
    )
    time.sleep(delay)

# ... (double_tap, long_press, swipe, back, home, launch_app implementations remain the same) ...
# 为了完整性，这里补全剩余函数（与之前提供的版本一致即可）

def double_tap(x: int | list, y: int | None = None, device_id: str | None = None, delay: float = 1.0) -> None:
    if isinstance(x, (list, tuple)): fx, fy = int(x[0]), int(x[1])
    else: fx, fy = int(x), int(y)
    adb_prefix = _get_adb_prefix(device_id)
    cmd = ["shell", "input", "tap", str(fx), str(fy)]
    subprocess.run(adb_prefix + cmd, capture_output=True)
    time.sleep(0.1)
    subprocess.run(adb_prefix + cmd, capture_output=True)
    time.sleep(delay)

def long_press(x: int | list, y: int | None = None, duration_ms: int = 1000, device_id: str | None = None, delay: float = 1.0) -> None:
    if isinstance(x, (list, tuple)): fx, fy = int(x[0]), int(x[1])
    else: fx, fy = int(x), int(y)
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(
        adb_prefix + ["shell", "input", "swipe", str(fx), str(fy), str(fx), str(fy), str(duration_ms)],
        capture_output=True,
    )
    time.sleep(delay)

def swipe(start_x: int | list, start_y: int | None, end_x: int | None = None, end_y: int | None = None, duration_ms: int | None = None, device_id: str | None = None, delay: float = 1.0) -> None:
    if isinstance(start_x, (list, tuple)):
        s_x, s_y = int(start_x[0]), int(start_x[1])
        if isinstance(start_y, (list, tuple)): e_x, e_y = int(start_y[0]), int(start_y[1])
        else: e_x, e_y = int(end_x), int(end_y)
    else:
        s_x, s_y = int(start_x), int(start_y)
        e_x, e_y = int(end_x), int(end_y)
    
    adb_prefix = _get_adb_prefix(device_id)
    if duration_ms is None:
        dist_sq = (s_x - e_x) ** 2 + (s_y - e_y) ** 2
        duration_ms = max(500, min(int(dist_sq / 1000), 2000))

    subprocess.run(
        adb_prefix + ["shell", "input", "swipe", str(s_x), str(s_y), str(e_x), str(e_y), str(duration_ms)],
        capture_output=True,
    )
    time.sleep(delay)

def back(device_id: str | None = None, delay: float = 1.0) -> None:
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(adb_prefix + ["shell", "input", "keyevent", "4"], capture_output=True)
    time.sleep(delay)

def home(device_id: str | None = None, delay: float = 1.0) -> None:
    adb_prefix = _get_adb_prefix(device_id)
    subprocess.run(adb_prefix + ["shell", "input", "keyevent", "KEYCODE_HOME"], capture_output=True)
    time.sleep(delay)

def launch_app(app_name: str, device_id: str | None = None, delay: float = 1.0) -> bool:
    if app_name not in APP_PACKAGES: return False
    adb_prefix = _get_adb_prefix(device_id)
    package = APP_PACKAGES[app_name]
    subprocess.run(
        adb_prefix + ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
        capture_output=True,
    )
    time.sleep(delay)
    return True