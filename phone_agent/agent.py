"""Main PhoneAgent class for orchestrating phone automation."""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action
# 假设有一个基础的 Screenshot 类定义，这里为了类型提示加上
# from phone_agent.adb import Screenshot 
from phone_agent.adb import get_current_app, get_screenshot
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder


@dataclass
class AgentConfig:
    """Configuration for the PhoneAgent."""

    max_steps: int = 100
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None
    # [新增] 包含当前步骤的截图数据，方便外部调试或展示
    screenshot: Any | None = None  # 类型应为 phone_agent.adb.Screenshot


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.
    ... (Docstring kept the same) ...
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        # [优化] 明确 _context 的类型提示，有助于 IDE 推断
        self._context: list[dict[str, Any]] = []
        self._step_count = 0

    def run(self, task: str) -> str:
        """
        Run the agent to complete a task.
        ... (Docstring kept the same) ...
        """
        self.reset() # [优化] 使用 reset() 方法统一初始化状态

        # First step with user prompt
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.
        ... (Docstring kept the same) ...
        """
        # [优化] 使用更明确的判断属性，而不是检查列表长度
        is_first = self._step_count == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1

        # 1. Capture current screen state
        try:
            screenshot = get_screenshot(self.agent_config.device_id)
            current_app = get_current_app(self.agent_config.device_id)
        except Exception as e:
            # [新增] ADB 操作可能会失败，需要捕获异常
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True, # 或者 False，取决于策略。如果无法获取屏幕，通常意味着无法继续。
                action=None,
                thinking="",
                message=f"Failed to capture screen or app info: {e}",
                screenshot=None
            )

        # 2. Build messages
        # [优化] 将公共的屏幕信息构建逻辑移出 if/else 块，减少重复代码 (DRY原则)
        screen_info = MessageBuilder.build_screen_info(current_app)

        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )
            text_content = f"{user_prompt}\n\n{screen_info}"
        else:
            text_content = f"** Screen Info **\n\n{screen_info}"

        self._context.append(
            MessageBuilder.create_user_message(
                text=text_content, image_base64=screenshot.base64_data
            )
        )

        # 3. Get model response
        try:
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            # [优化] 模型调用失败时，确保返回包含当前截图的 StepResult，方便调试
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
                screenshot=screenshot
            )

        # 4. Parse action from response
        try:
            action = parse_action(response.action)
        except ValueError as e:
            if self.agent_config.verbose:
                print(f"Action parsing failed: {e}") # [优化] 打印具体的解析错误
                # traceback.print_exc() # 可选：如果需要完整的堆栈信息
            # 如果解析失败，强制结束，避免执行未知动作
            action = finish(message=f"Failed to parse model action. Raw output: {response.action}")

        if self.agent_config.verbose:
            # Print thinking process
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
            print(response.thinking)
            print("-" * 50)
            print(f"🎯 {msgs['action']}:")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # 5. Remove image from context to save space
        # 这一点非常重要，保持上下文窗口精简
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # 6. Execute action
        action_execution_error = None
        try:
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            action_execution_error = str(e)
            # 原有逻辑：如果动作执行失败，尝试执行一个 'finish' 动作来优雅退出。
            # 这是一种防御性编程，确保 'result' 变量被正确赋值，以便后续逻辑使用。
            # 注意：如果 ADB 彻底挂了，这个 finish 也可能会失败。
            result = self.action_handler.execute(
                finish(message=f"Action execution failed: {e}"), screenshot.width, screenshot.height
            )

        # 7. Add assistant response to context
        # 将模型的原始思考和回答重新组合放入历史记录，保持对话连贯性
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )

        # 8. Check if finished
        # 检查模型是否决定结束，或者动作执行器是否决定结束（例如人工接管）
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "🎉 " + "=" * 48)
            final_message = result.message or action.get("message", msgs["done"])
            if action_execution_error:
                 # 如果是因错误而结束，修改提示前缀
                 print(f"❌ Task Ended with Error: {final_message}")
            else:
                 print(f"✅ {msgs['task_completed']}: {final_message}")
            print("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
            screenshot=screenshot, # [新增] 返回截图
        )

    # Property docstrings added for clarity
    @property
    def context(self) -> list[dict[str, Any]]:
        """Get a copy of the current conversation context (message history)."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current number of steps executed in the current task."""
        return self._step_count