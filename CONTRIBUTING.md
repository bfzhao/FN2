# Contributing to FN² — Fractal Negative Feedback Node Agent Framework

Thank you for your interest in contributing to FN² — Fractal Negative Feedback Node Agent Framework!

FN² 是一个早期、极简的项目，目标是探索**负反馈闭环 + 分形递归**这种控制架构的可能性。我们不追求短期 demo 或 leaderboard 排名，而是希望和真正对这个方向有共鸣的人一起，把骨架打得更扎实、更可扩展。

欢迎任何形式的贡献：从 prompt 调优、工具实现，到架构提案、测试、文档，都很有价值。但请注意，我们更看重**深度**而非**数量**。

## Before You Start

我们强烈建议先完整阅读：

- [README.md](./README.md)（尤其是 Design Philosophy 部分）
- 当前的 [issues](https://github.com/你的用户名/fn2/issues) 和 [discussions](https://github.com/你的用户名/fn2/discussions)（如果有）

如果你对以下问题有强烈共鸣，再考虑贡献会更高效：

- 你是否对当前大多数 Agent “看起来聪明、实际很脆”感到不满？
- 你是否相信**结构化的负反馈、显式验证、不确定性管理**是长期可靠的关键？
- 你是否愿意花时间调 prompt、设计工具、思考 memory，而不是只想快速跑通一个 demo？

如果答案是“是”，那我们很可能是在同一条路上。

## Contribution Types & How to Proceed

### 1. Prompt Engineering & Small Improvements（最欢迎的快速贡献）

当前最大的瓶颈是 Analyzer / Matcher / Synthesizer 的提示词稳定性。

你可以：

- 直接 fork & PR 修改 `llm_analyzer_prompt.py`、`matcher_prompt.py` 等文件
- 在 PR 描述中说明：改动理由、测试过的任务示例、效果对比（哪怕是主观感受）

这类 PR 我们会优先 review & merge。

### 2. New Tools / Skills

工具链是当前最缺的部分。优先级最高的几个：

- web search（可靠的搜索引擎接口）
- python code execution（安全的本地代码执行沙箱）
- file read/write（本地文件操作）
- browser automation 或 page summarization

实现方式建议：

- 在 `execution_engine.py` 中注册新工具
- 提供清晰的输入/输出 schema
- 写简单测试（哪怕是 dryrun 下的 mock）

### 3. Architecture Proposals & Deep Discussions

如果你有关于以下方向的想法，请**先开 issue**，用 `Proposal:` 前缀标题：

- 子任务结果的智能汇总与合成逻辑
- 更好的不确定性评估 & 重试/升级策略
- 长期记忆模式（向量存储？情节记忆？键值缓存？）
- 多 Agent 协作原语（角色分工、通信协议）
- 反思/批判环路的独立模块化
- Human-in-the-loop 的更优雅设计

我们非常欢迎这类 issue，甚至比代码 PR 更优先讨论。

**重要**：大范围重构或新模块的 PR，请**先在 issue 中达成共识**，否则可能被 close。

### 4. Tests, Docs & Quality

- 为 Board 状态转换、事件流写单元测试（pytest）
- 改进 README、添加架构图（用 draw.io / excalidraw）
- 写使用示例、设计决策记录（ADRs）
- 修复 bug、改进 trace 可读性

这类贡献对项目的长期可维护性非常重要。

## Development Setup

```bash
# 推荐使用 uv / pdm / poetry 管理依赖
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 运行交互模式
python main.py
```

- 关闭 dryrun：`config.py` 中 `runtime["dryrun"] = False`
- 启用 trace：`runtime["trace"]` 各组件设为 True

## Code Style & Conventions

- Formatting: black + isort
- Linting: flake8 / ruff
- Type hints: 鼓励在关键模块使用（mypy 可选）
- Commit messages: 英文，简洁，Conventional Commits 风格可选（feat: / fix: / refactor: 等）

示例：
```
feat: add web_search tool to execution engine
fix: prevent infinite clarification in analyzer prompt
docs: update CONTRIBUTING with proposal guidelines
```

## Communication

- Issues & Discussions 是主要沟通渠道
- X（Twitter）：@bfzhao（欢迎 DM 聊想法）
- 如果你想深度讨论架构，欢迎直接 issue 或 DM，我们可以 voice chat / video call

## Recognition

所有贡献者都会被记录在项目历史中（未来会加 CONTRIBUTORS.md）。  
我们更看重你的想法和深度参与，而不是 PR 数量。

感谢你阅读到这里。  
如果你觉得“这就是我想做的方向”，欢迎随时动手或开 issue。

一起把负反馈 + 分形递归这条路走得更远。

— bingfeng / @bfzhao
