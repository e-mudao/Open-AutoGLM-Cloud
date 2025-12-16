# Open-AutoGLM-Cloud

[Read this in English.](./README_en.md)

## 项目介绍

**Open-AutoGLM-Cloud** 是 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) 的轻量化云端适配版本。

原项目缺省依赖vLLM推理和本地的 `AutoGLM-Phone-9B` 模型，本项目将其核心推理引擎替换为 **智谱 AI 的 AutoGLM-Phone 云端 API**（用GLM-4.6V感觉效果也可以）。这意味着你可以在任何普通电脑（如 MacBook Air、Windows 笔记本）上运行这一强大的手机智能体，无需安装 vLLM、PyTorch 等重型依赖，也无需下载数百 GB 的模型权重。

本项目保留了原版强大的规划与控制能力，并针对云端场景进行了深度优化：
- 🧠 **支持 Native Thinking**：开启 深度思考模式，处理复杂长链条任务。
- 📱 **完美分辨率适配**：重构坐标系统，自动适配任意分辨率，解决点击偏移问题。
- 👆 **拟人化操作**：底层增加随机抖动（Jitter）机制，有效防止误触状态栏或点击死像素点。
- 🚀 **极速响应**：内置智能图片压缩策略，显著降低 API 延迟。

> ⚠️ 本项目仅供研究和学习使用。严禁用于非法获取信息、干扰系统或任何违法活动。

## 核心特性

| 特性 | Open-AutoGLM (原版) | Open-AutoGLM-Cloud (本项目) |
| :--- | :--- | :--- |
| **硬件要求** | 需要高端显卡 (24GB+ VRAM) | **任意电脑 (无 GPU 要求)** |
| **模型部署** | 本地 vLLM / SGLang | **无需部署 (直接调用 API)** |
| **模型** | AutoGLM-Phone-9B | **云端AutoGLM-Phone-9B ** |
| **安装体积** | 数百 GB | **< 100 MB** |

## 环境准备

### 1. Python 环境
建议使用 Python 3.10 及以上版本。

### 2. 获取 API Key
请前往 [智谱 AI 开放平台](https://open.bigmodel.cn/) 注册并获取 API Key。

### 3. ADB (Android Debug Bridge)
1. 下载官方 ADB [安装包](https://developer.android.com/tools/releases/platform-tools?hl=zh-cn)。
2. 配置环境变量：
   - **MacOS**: `export PATH=${PATH}:~/path/to/platform-tools`
   - **Windows**: 将解压路径添加到系统环境变量 Path 中。

### 4. Android 设备准备
1. 准备一台 Android 7.0+ 的手机或模拟器。
2. **开启开发者模式**：设置 -> 关于手机 -> 连续点击版本号。
3. **开启 USB 调试**：设置 -> 开发者选项 -> USB 调试。
4. **安装 ADB Keyboard**（重要）：
   - 下载 [ADBKeyboard.apk](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk)。
   - 安装并**在输入法设置中启用** `ADB Keyboard`。

## 快速开始

### 1. 安装依赖

本项目移除了 PyTorch 和 vLLM 等重型依赖，仅需安装轻量级库：

```bash
pip install -r requirements.txt 
pip install -e .
```

### 2. 设置 API Key

在终端中设置环境变量（或将其写入 `~/.zshrc` / `~/.bashrc`）：

```bash
export ZHIPUAI_API_KEY="你的_API_Key_粘贴在这里"
```

### 3. 连接手机

使用 USB 连接手机，并确认设备已连接：

```bash
adb devices
# 应显示：List of devices attached
# xxxxxxxx   device
```

### 4. 运行 Agent

直接运行 `main.py` 即可开始：

```bash
# 交互模式（推荐）
python main.py

# 单次任务模式
python main.py "打开小红书搜索智谱用户，给前三个帖子点赞"

```

## 配置说明

### 环境变量

| 变量 | 描述 | 默认值 |
| :--- | :--- | :--- |
| `ZHIPUAI_API_KEY` | **(必填)** 智谱 API Key | 无 |
| `PHONE_AGENT_MODEL` | 使用的模型名称 | `autoglm-phone` |
| `PHONE_AGENT_BASE_URL` | API 地址 | `https://open.bigmodel.cn/api/paas/v4/` |

### 配置文件

主要配置文件位于 `phone_agent/config/`：
- `prompts.py`: 系统提示词（System Prompt）。
- `apps.py`: 支持的应用包名映射。

## 远程调试

支持通过 WiFi 控制设备：

1. **开启无线调试**：确保手机和电脑在同一 WiFi。
2. **连接设备**：
   ```bash
   adb connect 192.168.1.XX:5555
   ```
3. **运行脚本**：
   ```bash
   python main.py "你的任务"
   ```

## 致谢与引用

本项目 Fork 自 [Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)，感谢原作者团队的开源贡献。
