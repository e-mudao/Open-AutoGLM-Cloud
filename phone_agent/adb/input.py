"""Input utilities for Android device text input."""

import base64
import subprocess
import time
from typing import Optional


def type_text(text: str, device_id: str | None = None) -> None:
    """
    Type text into the currently focused input field using ADB Keyboard.

    Args:
        text: The text to type.
        device_id: Optional ADB device ID for multi-device setups.

    Note:
        Requires ADB Keyboard to be installed on the device.
    """
    # 🎯 新增日志: 方便看到 AI 到底想输入什么
    print(f"⌨️ Typing: \"{text}\"")

    adb_prefix = _get_adb_prefix(device_id)
    # 使用 Base64 传输以支持中文
    encoded_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")

    subprocess.run(
        adb_prefix
        + [
            "shell",
            "am",
            "broadcast",
            "-a",
            "ADB_INPUT_B64",
            "--es",
            "msg",
            encoded_text,
        ],
        capture_output=True,
        text=True,
    )


def clear_text(device_id: str | None = None) -> None:
    """
    Clear text in the currently focused input field.
    """
    print("⌨️ Clearing text...")
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"],
        capture_output=True,
        text=True,
    )


def detect_and_set_adb_keyboard(device_id: str | None = None) -> str:
    """
    Detect current keyboard and switch to ADB Keyboard if needed.
    
    Fix: Explicitly enables the keyboard before setting it to ensure it works.
    Returns: The original keyboard IME identifier.
    """
    adb_prefix = _get_adb_prefix(device_id)
    adb_ime = "com.android.adbkeyboard/.AdbIME"

    # 1. 获取当前输入法
    result = subprocess.run(
        adb_prefix + ["shell", "settings", "get", "secure", "default_input_method"],
        capture_output=True,
        text=True,
    )
    current_ime = (result.stdout + result.stderr).strip()

    # 2. 如果当前不是 ADB Keyboard，则进行切换
    if adb_ime not in current_ime:
        print(f"🔄 Switching input method to ADB Keyboard (Old: {current_ime})")
        
        # 🎯 关键修复 A: 先强制【启用】该输入法
        # 很多手机安装后默认是禁用的，直接 set 会失败
        subprocess.run(
            adb_prefix + ["shell", "ime", "enable", adb_ime],
            capture_output=True,
            text=True,
        )
        
        # 🎯 关键修复 B: 设置为默认输入法
        subprocess.run(
            adb_prefix + ["shell", "ime", "set", adb_ime],
            capture_output=True,
            text=True,
        )
        
        # 🎯 关键修复 C: 等待系统切换完成 (防止切换太快导致输入丢失)
        time.sleep(1.0)

    # 预热一下 (发送一个空字符，确保广播接收器已唤醒)
    type_text("", device_id)

    return current_ime


def restore_keyboard(ime: str, device_id: str | None = None) -> None:
    """
    Restore the original keyboard IME.
    """
    # 如果原输入法为空，或者原输入法就是 ADB Keyboard，则不恢复
    if not ime or "com.android.adbkeyboard" in ime:
        return

    print(f"🔄 Restoring original input method: {ime}")
    adb_prefix = _get_adb_prefix(device_id)

    subprocess.run(
        adb_prefix + ["shell", "ime", "set", ime], capture_output=True, text=True
    )


def _get_adb_prefix(device_id: str | None) -> list:
    """Get ADB command prefix with optional device specifier."""
    if device_id:
        return ["adb", "-s", device_id]
    return ["adb"]