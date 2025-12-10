#!/usr/bin/env python3
"""
Phone Agent CLI - Cloud API Edition (ZhipuAI GLM-4.5V)
"""

import argparse
import os
import shutil
import subprocess
import sys

from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.config.apps import list_supported_apps
from phone_agent.model import ModelConfig

def main():
    parser = argparse.ArgumentParser(description="Phone Agent (GLM-4.5v)")
    parser.add_argument("task", nargs="?", type=str, help="Task to execute")
    parser.add_argument("--list-apps", action="store_true")
    args = parser.parse_args()

    if args.list_apps:
        for app in sorted(list_supported_apps()):
            print(f"- {app}")
        return

    # Check Key
    if not os.getenv("ZHIPUAI_API_KEY"):
        print("❌ Error: Environment variable 'ZHIPUAI_API_KEY' is missing.")
        sys.exit(1)

    # Check ADB
    if shutil.which("adb") is None:
        print("❌ Error: ADB not found.")
        sys.exit(1)

    # Configs
    model_config = ModelConfig() # Defaults to GLM-4.5v + Thinking
    agent_config = AgentConfig(max_steps=50, verbose=True)

    try:
        agent = PhoneAgent(model_config=model_config, agent_config=agent_config)
    except Exception as e:
        print(f"❌ Init failed: {e}")
        sys.exit(1)

    print("=" * 50)
    print("🤖 Agent initialized with GLM-4.5v (OpenAI-Compatible Mode)")
    print("📱 Resolution: 720x1604")
    print("🧠 Thinking: Enabled")
    print("=" * 50)

    if args.task:
        agent.run(args.task)
    else:
        while True:
            try:
                task = input("\nTask (q to quit): ").strip()
                if task.lower() == 'q': break
                if task:
                    agent.run(task)
                    agent.reset()
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    main()
