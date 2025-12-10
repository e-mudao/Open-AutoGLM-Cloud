"""Model client for AI inference using OpenAI-compatible API (ZhipuAI GLM-4.6v)."""

import json
import os
import base64
import io
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from openai import OpenAI
from PIL import Image

@dataclass
class ModelConfig:
    """Configuration for the AI model."""
    base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    api_key: str = os.getenv("ZHIPUAI_API_KEY", "")
    model_name: str = "glm-4.6v"
    max_tokens: int = 4096
    temperature: float = 0.5
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    timeout: float = 120.0
    extra_body: dict[str, Any] = field(
        default_factory=lambda: {
            "thinking": {
                "type": "enabled"
            }
        }
    )

@dataclass
class ModelResponse:
    """Response from the AI model."""
    thinking: str
    action: str
    raw_content: str

class ModelClient:
    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        
        if not self.config.api_key:
            self.config.api_key = os.getenv("ZHIPUAI_API_KEY", "EMPTY")

        timeout_config = httpx.Timeout(timeout=self.config.timeout, connect=10.0)
        
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            timeout=timeout_config,
        )

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """Send a request to the model."""
        try:
            print(f"\n🚀 [Model] Sending request to {self.config.model_name} (Thinking Enabled)...")
            
            processed_messages = self._process_messages(messages)

            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=processed_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                extra_body=self.config.extra_body,
                stream=False
            )

            message_obj = response.choices[0].message
            content = message_obj.content or ""
            
            # 提取 Native Reasoning
            reasoning_content = ""
            if hasattr(message_obj, "reasoning_content"):
                reasoning_content = getattr(message_obj, "reasoning_content")
            if not reasoning_content and hasattr(message_obj, "model_extra") and message_obj.model_extra:
                reasoning_content = message_obj.model_extra.get("reasoning_content", "")

            # 调试日志
            # print(f"📝 [Raw Content]: {content[:100]}...") 
            if reasoning_content:
                print(f"🧠 [Reasoning]: {reasoning_content[:100]}...")

            # 解析
            thinking, action = self._parse_response(content, reasoning_content)
            
            # 如果解析出的动作看起来像是一个 finish 动作且包含错误信息，
            # 可能是因为解析失败，我们保留原始信息以便调试
            return ModelResponse(thinking=thinking, action=action, raw_content=content)

        except Exception as e:
            print(f"❌ [Model] API Request Error: {e}")
            return ModelResponse(
                thinking="Error", 
                action="finish(message='API call failed')", 
                raw_content=str(e)
            )

    def _process_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        new_messages = []
        for msg in messages:
            new_msg = msg.copy()
            new_content = []
            if isinstance(msg.get("content"), list):
                for item in msg["content"]:
                    new_item = item.copy()
                    if new_item.get("type") == "image_url":
                        url = new_item["image_url"]["url"]
                        if url.startswith("data:image"):
                            try:
                                header, encoded = url.split(",", 1)
                                compressed_b64 = self._resize_image_base64(encoded, max_size=1604)
                                new_item["image_url"]["url"] = f"{header},{compressed_b64}"
                            except Exception:
                                pass
                    new_content.append(new_item)
                new_msg["content"] = new_content
            new_messages.append(new_msg)
        return new_messages

    def _resize_image_base64(self, base64_str: str, max_size: int = 1604) -> str:
        try:
            image_data = base64.b64decode(base64_str)
            img = Image.open(io.BytesIO(image_data))
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            width, height = img.size
            if max(width, height) > max_size:
                ratio = max_size / max(width, height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"   ℹ️ 图片已缩放: {width}x{height} -> {new_width}x{new_height}")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            new_data = buffer.getvalue()
            return base64.b64encode(new_data).decode('utf-8')
        except Exception:
            return base64_str

    def _parse_response(self, content: str, reasoning_content: str = "") -> tuple[str, str]:
        """
        鲁棒解析器：
        1. 优先使用 reasoning_content 作为 thinking。
        2. 使用正则暴力提取 do(...) 或 finish(...) 作为 action，忽略周围的乱码。
        """
        if not content and not reasoning_content:
            return "", "finish(message='Empty response')"

        # 1. 确定 Thinking 内容
        thinking = reasoning_content
        
        # 如果 reasoning_content 为空，尝试从 content 里的 <think> 标签或 XML 结构提取
        if not thinking:
            if "<think>" in content:
                parts = content.split("</think>")
                thinking = parts[0].replace("<think>", "").strip()
            elif "<answer>" in content:
                 parts = content.split("<answer>")
                 thinking = parts[0].strip()

        # 2. 提取 Action 内容 (这是报错的核心修复点)
        action = ""
        
        # 清理常见的 GLM-4.6v 特殊标记
        clean_content = content.replace("<|begin_of_box|>", "").replace("<|end_of_box|>", "")
        
        # 正则表达式匹配标准的 agent 动作指令
        # 匹配 do(...) 或 finish(...)，允许换行，非贪婪匹配
        # pattern 解释: (do|finish) 开始，后面跟任意空白，然后是左括号，然后是任意字符直到右括号
        action_pattern = r"(do|finish)\s*\(.*?\)"
        
        match = re.search(action_pattern, clean_content, re.DOTALL)
        
        if match:
            # 提取匹配到的纯净指令
            action = match.group(0)
            # 移除可能存在的换行符，变成单行
            action = action.replace("\n", " ").strip()
        else:
            # 如果正则没匹配到，回退到原来的 XML 解析逻辑（虽然可能已经失败了）
            if "<answer>" in content:
                parts = content.split("<answer>", 1)
                action = parts[1].replace("</answer>", "").strip()
            else:
                # 最后的兜底：如果实在提取不出，但内容里有 do(，可能是正则没写好，直接清理标记返回
                if "do(" in clean_content or "finish(" in clean_content:
                     # 尝试简单的字符串截取
                     start = clean_content.find("do(")
                     if start == -1: start = clean_content.find("finish(")
                     if start != -1:
                         action = clean_content[start:].strip()
                else:
                    action = clean_content.strip()

        # 调试日志：看看最终提取出了什么
        if action != content:
            print(f"🎯 [Action Extracted]: {action}")
            
        return thinking, action

class MessageBuilder:
    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(text: str, image_base64: str | None = None) -> dict[str, Any]:
        content = []
        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                },
            })
        content.append({"type": "text", "text": text})
        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)
