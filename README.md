> 独立 DeepSeek 入口：`python -m narrative.autorun --scenario narrative/scenarios/society.json --rounds 3 --steps-per-round 6 --max-calls 80 --output output/my-story`。无需 GPT 或开发助手驻场；详见 [运行说明](docs/narrative-v1.md)。

## 本 Fork：通用叙事实验架构（开发中）

新增轻量入口 `python -m narrative.run`。使用 **deepseek-flash**；本地 `.env` 自动读取并被 Git 忽略，Jev 可选，运行时不依赖 GPT。原版保留作为对照。

阅读 [新版设计与运行说明](docs/narrative-v1.md)、[真实验证报告及未完成项](docs/validation-v1.md)、[执行计划](docs/plans/2026-10-11-narrative-v1.md)。目前工程流程可运行，创作效果尚未验收。新入口仅需 Python 3.11+ 标准库；下方安装说明属于原版。

---
<h1 align="center">StoryBox</h1>

<p align="center">
    <a href="https://ojs.aaai.org/index.php/AAAI/article/view/40288"><img src="https://img.shields.io/badge/AAAI_2026-Paper-4285F4?style=for-the-badge&logoColor=white" style="border-radius: 10px;"></a>
    &nbsp;&nbsp;
    <a href="https://arxiv.org/abs/2510.11618"><img src="https://img.shields.io/badge/Arxiv-2510.11618-A52C25?style=for-the-badge&logo=arxiv&logoColor=white" style="border-radius: 10px;"></a>
    &nbsp;&nbsp;
    <a href="https://storyboxproject.github.io/"><img src="https://img.shields.io/badge/Website-Project-2962FF?style=for-the-badge&logoColor=white" style="border-radius: 10px;"></a>
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Task-Story_Generation-6d4aff?style=for-the-badge&logo=task&logoColor=white" style="border-radius: 10px;">
    &nbsp;&nbsp;
    <a href="https://opensource.org/license/MIT"><img src="https://img.shields.io/badge/License-MIT-009CAB?style=for-the-badge&logo=book&logoColor=white" style="border-radius: 10px;"></a>
</p>

## 📝 Introduction

This is the repository for the paper [StoryBox: Collaborative Multi-Agent Simulation for Hybrid Bottom-Up Long-Form Story Generation Using Large Language Models](https://ojs.aaai.org/index.php/AAAI/article/view/40288), accepted by **AAAI 2026**.

![Framework](assets/framework.jpg)

**StoryBox** is a framework that leverages collaborative multi-agent simulation for hybrid bottom-up long-form story generation. By combining bottom-up character-driven agent interactions with top-down narrative planning, it dynamically constructs deep, coherent, and engaging story worlds.

## ⚙️ Installation

We use [uv](https://docs.astral.sh/uv/) for extremely fast Python package management. 

**1. Install `uv` (if you haven't already):**

Please refer to the official uv documentation for installation instructions.

**2. Clone the repository:**

```bash
git clone https://github.com/amcghm/StoryBox.git
cd StoryBox
```

**3. Install dependencies:**

```bash
uv sync
```

## 🛠️ Configuration

Before running the simulation, you need to configure the settings and set up your API key.

The main configuration file is located at `reverie/config/config.py`. You can adjust parameters such as the LLM model (`llm_model_name`), temperature, and sandbox settings here.

**Setting up the API Key:**

The configuration is designed to safely read your API key from environment variables. You can set it in your terminal before running the code:

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## 🚀 Quick Start

Once everything is installed and configured, you can start the StoryBox generation process directly using `uv`:

```bash
cd reverie
uv run run.py
```

The output logs, database, and story JSONs will be saved in the `output/` directory as specified in the configuration.

## 📚 Citation

If you find our work helpful in your research, please cite our paper:

```bibtex
@inproceedings{chen2026storybox,
  title     = {StoryBox: Collaborative Multi-Agent Simulation for Hybrid Bottom-Up Long-Form Story Generation Using Large Language Models},
  author    = {Chen, Zehao and Pan, Rong and Li, Haoran},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {40},
  number    = {36},
  pages     = {30359--30367},
  year      = {2026}
}
```

## ⚖️ License

<a href="https://opensource.org/license/MIT"><img src="https://img.shields.io/badge/License-MIT-009CAB?style=for-the-badge&logo=book&logoColor=white" style="border-radius: 10px;"></a>

This project is licensed under the [MIT License](https://opensource.org/license/MIT).
