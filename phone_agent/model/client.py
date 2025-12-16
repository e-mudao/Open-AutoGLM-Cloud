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
    
    # Model Settings
    model_name: str = "autoglm-phone"
    max_tokens: int = 4096
    temperature: float = 0.5  # Slightly higher for thinking models
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    timeout: float = 120.0
    
    # Enable Native Thinking
    extra_body: dict[str, Any] = field(
        default_factory=lambda: {
            "thinking": {
                "type": "enabled"
            }
        }
    )
    # 思考模式开关标记，用于逻辑控制
    thinking_enabled: bool = True

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
            print(f"\n🚀 [Model] Sending request to {self.config.model_name}...")
            
            # 1. Process Images (Compress)
            processed_messages = self._process_messages(messages)

            # 2. Call API
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

            # 3. Extract Content
            message_obj = response.choices[0].message
            content = message_obj.content or ""
            
            # Attempt to extract native reasoning_content
            reasoning_content = ""
            if hasattr(message_obj, "reasoning_content"):
                reasoning_content = getattr(message_obj, "reasoning_content")
            if not reasoning_content and hasattr(message_obj, "model_extra") and message_obj.model_extra:
                reasoning_content = message_obj.model_extra.get("reasoning_content", "")

            # Log partial reasoning for visibility
            if reasoning_content:
                print(f"🧠 [Reasoning]: {reasoning_content[:100]}...")

            # 4. Parse Action
            thinking, action = self._parse_response(content, reasoning_content)
            
            return ModelResponse(thinking=thinking, action=action, raw_content=content)

        except Exception as e:
            print(f"❌ [Model] API Request Error: {e}")
            return ModelResponse(
                thinking="Error", 
                action="finish(message='API call failed')", 
                raw_content=str(e)
            )

    def _process_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compress images to standard HD size for API efficiency."""
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
                                # Use 1920 as a safe generic max size
                                compressed_b64 = self._resize_image_base64(encoded, max_size=1920)
                                new_item["image_url"]["url"] = f"{header},{compressed_b64}"
                            except Exception:
                                pass
                    new_content.append(new_item)
                new_msg["content"] = new_content
            new_messages.append(new_msg)
        return new_messages

    def _resize_image_base64(self, base64_str: str, max_size: int = 1920) -> str:
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
                print(f"   ℹ️ Image resized: {width}x{height} -> {new_width}x{new_height}")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            new_data = buffer.getvalue()
            return base64.b64encode(new_data).decode('utf-8')
        except Exception:
            return base64_str

    def _parse_response(self, content: str, reasoning_content: str = "") -> tuple[str, str]:
        """Robust parser for mixed content."""
        if not content and not reasoning_content:
            return "", "finish(message='Empty response')"

        # 1. Determine Thinking
        thinking = reasoning_content
        if not thinking:
            if "<think>" in content:
                thinking = content.split("</think>")[0].replace("<think>", "").strip()
            elif "<answer>" in content:
                thinking = content.split("<answer>")[0].strip()

        # 2. Extract Action using Regex (Robust)
        # Matches: do(...) or finish(...)
        clean_content = content.replace("<|begin_of_box|>", "").replace("<|end_of_box|>", "")
        action_pattern = r"(do|finish)\s*\(.*?\)"
        match = re.search(action_pattern, clean_content, re.DOTALL)
        
        if match:
            action = match.group(0).replace("\n", " ").strip()
        else:
            # Fallback
            if "<answer>" in content:
                action = content.split("<answer>")[1].replace("</answer>", "").strip()
            else:
                action = clean_content.strip()

        if action != content:
            print(f"🎯 [Action]: {action}")
            
        return thinking, action

class MessageBuilder:
    # (Methods unchanged from original but required for completeness)
    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(text: str, image_base64: str | None = None) -> dict[str, Any]:
        content = []
        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"},
            })
        content.append({"type": "text", "text": text})
        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        if isinstance(message.get("content"), list):
            message["content"] = [item for item in message["content"] if item.get("type") == "text"]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)