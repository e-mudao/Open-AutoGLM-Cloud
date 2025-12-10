"""Action handler for processing AI model outputs."""

import time
import re
import ast  # 🎯 核心修复：引入 AST 用于解析字符串列表
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.adb import (
    back,
    clear_text,
    detect_and_set_adb_keyboard,
    double_tap,
    home,
    launch_app,
    long_press,
    restore_keyboard,
    swipe,
    tap,
    type_text,
)

@dataclass
class ActionResult:
    success: bool
    should_finish: bool
    message: str | None = None
    requires_confirmation: bool = False

class ActionHandler:
    def __init__(
        self,
        device_id: str | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.device_id = device_id
        self.confirmation_callback = confirmation_callback or self._default_confirmation
        self.takeover_callback = takeover_callback or self._default_takeover

    def execute(
        self, action: dict[str, Any], screen_width: int, screen_height: int
    ) -> ActionResult:
        """Execute the action and handle exceptions gracefully."""
        action_type = action.get("_metadata")

        if action_type == "finish":
            return ActionResult(True, True, message=action.get("message"))

        if action_type != "do":
            return ActionResult(False, True, message=f"Unknown action type: {action_type}")

        action_name = action.get("action")
        handler_method = self._get_handler(action_name)

        if handler_method is None:
            return ActionResult(False, False, message=f"Unknown action: {action_name}")

        try:
            return handler_method(action, screen_width, screen_height)
        except Exception as e:
            # 🎯 关键修复：打印详细错误堆栈，防止静默失败
            print(f"❌ Action Execution Error: {e}")
            return ActionResult(False, False, message=f"Action failed: {str(e)}")

    def _get_handler(self, action_name: str) -> Callable | None:
        handlers = {
            "Launch": self._handle_launch,
            "Tap": self._handle_tap,
            "Type": self._handle_type,
            "Type_Name": self._handle_type,
            "Swipe": self._handle_swipe,
            "Back": self._handle_back,
            "Home": self._handle_home,
            "Double Tap": self._handle_double_tap,
            "Long Press": self._handle_long_press,
            "Wait": self._handle_wait,
            "Take_over": self._handle_takeover,
            "Note": self._handle_note,
            "Call_API": self._handle_call_api,
            "Interact": self._handle_interact,
        }
        return handlers.get(action_name)

    def _convert_relative_to_absolute(
        self, element: Any, screen_width: int, screen_height: int
    ) -> tuple[int, int]:
        """
        Convert relative coordinates (0-1000) to absolute pixels.
        Robustly handles string inputs like "[899, 55]".
        """
        # 🎯 关键修复：如果传入的是字符串，先解析成列表
        if isinstance(element, str):
            element = element.strip()
            try:
                # 尝试用 AST 安全解析 "[x, y]"
                element = ast.literal_eval(element)
            except Exception:
                # 兜底：简单的正则提取数字
                nums = re.findall(r"\d+", element)
                if len(nums) >= 2:
                    element = [int(nums[0]), int(nums[1])]
        
        # 类型检查
        if not isinstance(element, (list, tuple)) or len(element) < 2:
            raise ValueError(f"Invalid element format: {element}")
        
        # 转换逻辑：归一化(0-1000) -> 像素
        x_ratio = float(element[0])
        y_ratio = float(element[1])
        
        x = int(x_ratio / 1000.0 * screen_width)
        y = int(y_ratio / 1000.0 * screen_height)
        return x, y

    def _handle_launch(self, action: dict, width: int, height: int) -> ActionResult:
        app_name = action.get("app")
        if not app_name:
            return ActionResult(False, False, "No app name specified")

        success = launch_app(app_name, self.device_id)
        if success:
            return ActionResult(True, False)
        return ActionResult(False, False, f"App not found: {app_name}")

    def _handle_tap(self, action: dict, width: int, height: int) -> ActionResult:
        element = action.get("element")
        if not element:
            return ActionResult(False, False, "No element coordinates")

        # 1. 坐标转换 (0-1000 -> Pixel)
        x, y = self._convert_relative_to_absolute(element, width, height)

        # 2. 敏感操作确认
        if "message" in action:
            if not self.confirmation_callback(action["message"]):
                return ActionResult(False, True, "User cancelled sensitive operation")

        # 3. 执行点击 (传入的是像素坐标)
        tap(x, y, self.device_id)
        return ActionResult(True, False)

    def _handle_type(self, action: dict, width: int, height: int) -> ActionResult:
        text = action.get("text", "")
        original_ime = detect_and_set_adb_keyboard(self.device_id)
        time.sleep(0.5)
        clear_text(self.device_id)
        time.sleep(0.5)
        type_text(text, self.device_id)
        time.sleep(0.5)
        restore_keyboard(original_ime, self.device_id)
        return ActionResult(True, False)

    def _handle_swipe(self, action: dict, width: int, height: int) -> ActionResult:
        start = action.get("start")
        end = action.get("end")
        if not start or not end: return ActionResult(False, False, "Missing coordinates")

        start_x, start_y = self._convert_relative_to_absolute(start, width, height)
        end_x, end_y = self._convert_relative_to_absolute(end, width, height)
        swipe(start_x, start_y, end_x, end_y, device_id=self.device_id)
        return ActionResult(True, False)

    def _handle_back(self, action: dict, width: int, height: int) -> ActionResult:
        back(self.device_id)
        return ActionResult(True, False)

    def _handle_home(self, action: dict, width: int, height: int) -> ActionResult:
        home(self.device_id)
        return ActionResult(True, False)

    def _handle_double_tap(self, action: dict, width: int, height: int) -> ActionResult:
        element = action.get("element")
        if not element: return ActionResult(False, False, "No element")
        x, y = self._convert_relative_to_absolute(element, width, height)
        double_tap(x, y, self.device_id)
        return ActionResult(True, False)

    def _handle_long_press(self, action: dict, width: int, height: int) -> ActionResult:
        element = action.get("element")
        if not element: return ActionResult(False, False, "No element")
        x, y = self._convert_relative_to_absolute(element, width, height)
        long_press(x, y, device_id=self.device_id)
        return ActionResult(True, False)

    def _handle_wait(self, action: dict, width: int, height: int) -> ActionResult:
        try:
            val = str(action.get("duration", "1")).replace("seconds", "").strip()
            time.sleep(float(val))
        except:
            time.sleep(1.0)
        return ActionResult(True, False)

    def _handle_takeover(self, action: dict, width: int, height: int) -> ActionResult:
        self.takeover_callback(action.get("message", "Intervention required"))
        return ActionResult(True, False)

    def _handle_note(self, action: dict, width: int, height: int) -> ActionResult:
        return ActionResult(True, False)

    def _handle_call_api(self, action: dict, width: int, height: int) -> ActionResult:
        return ActionResult(True, False)

    def _handle_interact(self, action: dict, width: int, height: int) -> ActionResult:
        return ActionResult(True, False, message="Interaction required")

    @staticmethod
    def _default_confirmation(message: str) -> bool:
        return input(f"⚠️ Confirm {message}? (y/n): ").lower() == 'y'

    @staticmethod
    def _default_takeover(message: str) -> None:
        input(f"✋ {message} (Press Enter when done)")

# --- Helper Functions for eval() environment ---
def do(**kwargs) -> dict[str, Any]:
    kwargs["_metadata"] = "do"
    return kwargs

def finish(**kwargs) -> dict[str, Any]:
    kwargs["_metadata"] = "finish"
    return kwargs

def parse_action(response: str) -> dict[str, Any]:
    """Parse action string safely."""
    try:
        response = response.strip()
        context = {"do": do, "finish": finish}
        # Use eval with restricted scope
        action = eval(response, {"__builtins__": None}, context)
        if isinstance(action, dict) and "_metadata" in action:
            return action
        raise ValueError("Result is not a dict")
    except Exception as e:
        # Fallback for simple finish
        if "finish" in response:
             return {"_metadata": "finish", "message": "Task Completed"}
        raise ValueError(f"Parse failed: {e}")