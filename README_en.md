# Open-AutoGLM-Cloud

[中文阅读](./README.md)


## Introduction

**Open-AutoGLM-Cloud** is a lightweight, cloud-native fork of [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM).

The original project relies on heavy local GPU resources to deploy the `AutoGLM-Phone-9B` model. This fork replaces the core inference engine with **Zhipu AI's GLM-4.6v Cloud API**. This allows you to run this powerful mobile agent on any standard computer (e.g., MacBook Air, Windows Laptop) without installing heavy dependencies like vLLM or PyTorch, and without downloading hundreds of GBs of model weights.

This project retains the powerful planning and control capabilities of the original while being deeply optimized for cloud scenarios:

- 🧠 **Native Thinking Support**: Enables GLM-4.6v's deep reasoning mode to handle complex, long-chain tasks.
- 📱 **Auto Resolution Adaptation**: Reconstructed coordinate system that automatically detects and adapts to any screen resolution (fixing click offset issues on non-standard devices).
- 👆 **Human-like Interaction**: Implements a random "Jitter" mechanism in the underlying driver to prevent mis-clicks on the status bar or dead pixels.
- 🚀 **Fast Response**: Built-in intelligent image compression strategy to significantly reduce API latency.
- 🛡️ **Robust Parsing**: A rewritten output parser that handles mixed outputs (reasoning trace + XML + text) gracefully.

> ⚠️ This project is for research and learning purposes only. Strictly prohibited for illegal information gathering, system interference, or any illegal activities.

## Key Features

| Feature | Open-AutoGLM (Original) | Open-AutoGLM-Cloud (This Repo) |
| :--- | :--- | :--- |
| **Hardware** | High-end GPU (24GB+ VRAM) | **Any Computer (No GPU req.)** |
| **Deployment** | Local vLLM / SGLang | **Zero Deployment (API Call)** |
| **Model** | AutoGLM-Phone-9B | **GLM-4.6v (Thinking Enabled)** |
| **Size** | 100 GB+ | **< 100 MB** |

## Prerequisites

### 1. Python Environment
Python 3.10 or higher is recommended.

### 2. Get API Key
Please register at the [Zhipu AI Open Platform](https://open.bigmodel.cn/) and obtain an API Key.

### 3. ADB (Android Debug Bridge)
1. Download the official [ADB Platform Tools](https://developer.android.com/tools/releases/platform-tools).
2. Configure environment variables:
   - **MacOS**: `export PATH=${PATH}:~/path/to/platform-tools`
   - **Windows**: Add the unzipped folder path to your System `Path`.

### 4. Android Device Setup
1. Prepare an Android device (Android 7.0+) or emulator.
2. **Enable Developer Mode**: Settings -> About Phone -> Tap "Build Number" 7 times.
3. **Enable USB Debugging**: Settings -> Developer Options -> USB Debugging.
4. **Install ADB Keyboard** (Crucial for text input):
   - Download [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk).
   - Install it: `adb install ADBKeyboard.apk`.
   - **Enable it in your phone's Settings -> System -> Languages & Input.**

## Quick Start

### 1. Install Dependencies

We have removed PyTorch, vLLM, and other heavy libraries. You only need lightweight dependencies:

```bash
pip install -r requirements.txt 
pip install -e .
```

### 2. Set API Key

Set the environment variable in your terminal (or add to `~/.zshrc` / `~/.bashrc`):

```bash
export ZHIPUAI_API_KEY="your_api_key_here"
```

### 3. Connect Device

Connect your phone via USB and ensure it is recognized:

```bash
adb devices
# Output should look like:
# List of devices attached
# xxxxxxxx   device
```

### 4. Run the Agent

Simply run `main.py` to start:

```bash
# Interactive Mode (Recommended)
python main.py

# Single Task Mode
python main.py "Open Little Red Book, search for Beijing food, and like the first 3 posts"

# List supported apps
python main.py --list-apps
```

## Configuration

### Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ZHIPUAI_API_KEY` | **(Required)** Zhipu API Key | None |
| `PHONE_AGENT_MODEL` | Model Name | `glm-4.6v` |
| `PHONE_AGENT_BASE_URL` | API Endpoint | `https://open.bigmodel.cn/api/paas/v4/` |

### Config Files

Key configuration files are located in `phone_agent/config/`:
- `prompts.py`: System prompts.
- `apps.py`: App package name mapping.

## Remote Debugging

You can control devices via WiFi:

1. **Enable Wireless Debugging**: Ensure phone and PC are on the same WiFi.
2. **Connect**:
   ```bash
   adb connect 192.168.1.XX:5555
   ```
3. **Run**:
   ```bash
   python main.py "Your task here"
   ```

## Acknowledgments & Citation

This project is a fork of [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM). We thank the original authors for their open-source contribution.


```
