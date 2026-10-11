# StoryBox 高手局组件调研 v1

日期：2026-10-11

目标：调研现有 GitHub / 论文中的狼人杀、Avalon、社交推理、谈判和多智能体博弈框架，判断哪些可以直接成为 StoryBox 的底座，哪些只能作为算法蓝本，并明确我们真正缺失的“高手局”组件。

## 结论先行

StoryBox 目前已经有 World / Event Arc / Game / Scene / Round / Action、信息隔离、并发 Game、主持人、收敛和 replay 结构。真正短板不在规则引擎，而在玩家侧：

1. 没有可校准的 belief state；
2. 没有 opponent / intent model；
3. 没有 counterfactual planning / rollout；
4. 没有把“战略意图”和“自然语言发言”严格分层；
5. 没有 self-play -> evaluation -> strategy update 的闭环；
6. 没有高手局级别的 per-turn evaluation，只看结果或剧情是否成立远远不够。

因此建议新增独立组件：`StoryBox Strategic Cognition Kernel`（SCK），作为角色决策层，位于 StoryBox world/runtime 与 Storyteller prose 之间。

---

## S 级参考：强烈建议作为架构基准

### 1. Meta Cicero / Diplomacy

Repo: `facebookresearch/diplomacy_cicero`

公开信号：约 1430 stars / 167 forks；Science 论文；代码已归档。

最值得借的不是 Diplomacy 规则，而是整体拆分：

- 战略规划与语言生成分离；
- 先预测 / 采样其他玩家可能的 joint actions；
- 对候选行动做 rollout/value；
- bilateral / correlated planning；
- 语言服务于计划，而不是语言模型自己边说边决定战略。

这与 StoryBox 的方向高度一致。我们不应把整个 Cicero 当依赖：代码老、依赖重、领域专用；但它证明了“LM + planning”比纯聊天 agent 更接近高手局。

### 2. AvalonBench + Strategist

Repo: `jonathanmli/Avalon-LLM`

公开信号：约 164 stars / 16 forks；AvalonBench；Strategist 被 ICLR 2025 接收。

关键机制：

- information set / private role state；
- legal action enumeration；
- belief / side inference；
- MCTS / rollout；
- LLM 生成高层 strategy / value heuristic；
- self-play 反馈再更新策略；
- discussion 与 action intent 分离。

Strategist 的核心价值在“bi-level tree search”：上层是语言描述的策略 / value heuristic，下层通过 search/self-play 检验执行效果。

注意：GitHub metadata 未声明 license，因此适合按论文重实现，不建议直接复制源码。

### 3. TextArena

Repo: `TextArena/TextArena`

公开信号：约 430 stars / 100 forks；仍活跃；MIT；100+ text game environments；NeurIPS 2025 MindGames / self-play RL 生态。

最适合直接借的部分：

- Gym-like `Env` abstraction；
- env registry；
- standardized reset/step/state interface；
- 大量现成游戏作为外部压力测试；
- SecretMafia、Negotiation、Diplomacy、TwoRoomsAndABoom 等环境；
- self-play / leaderboard / training harness。

建议：不要把 TextArena 变成 StoryBox 本体；做一个 adapter，让我们的 SCK agent 能去 TextArena 玩现成游戏。这样可以立刻知道“我们的高手局 agent 到底强不强”。

### 4. SOTOPIA

Repo: `sotopia-lab/sotopia`

公开信号：约 337 stars / 50 forks；MIT；ICLR 2024 Spotlight。

它不是社交推理高手局 planner，但非常适合补另一半：

- 开放式社会目标；
- 社交能力不只等于赢；
- 多维评价；
- 人际关系、礼貌、目标冲突、社会规范。

StoryBox 最终不是狼人杀模拟器，SOTOPIA 适合作为“非零和社会行为”的外部 benchmark。

---

## A 级参考：适合抽模块 / 做测试

### 5. Google Werewolf Arena

Repo: `google/werewolf_arena`

约 48 stars / 18 forks；Apache-2.0；2025 已归档。

关键价值：

- dynamic turn-taking via bidding；
- 谁想说话本身就是 signal；
- private reasoning / bids / votes / prompts 可回放；
- tournament-style evaluation。

建议借：speaker bidding / turn scheduler + replay viewer 思路。

### 6. AIWolf Project / AIWolf Contest

长期运行的人狼知能竞赛；协议组 + 自然语言组。公开比赛一次决赛可跑约 36 万局，且有 finalist source/logs。

价值：

- 真正长期多人对局的稳定协议；
- 角色分项胜率；
- 大规模 tournament 而非 demo；
- NLP 评价明确要求：对话自然、上下文一致、行动和发言一致、角色表现连贯。

建议把 AIWolf logs / finalist strategy 当“高手局行为数据集”和回归测试，而非直接嵌入 runtime。

### 7. deepwolf

Repo: `JuneQQQ/deepwolf`

MIT；项目较新、stars 很少，但工程方向很对：

- strict seeded rules engine；
- self-play；
- reasoning trace；
- speaker bidding；
- belief model；
- Brier score / calibration。

特别值得借的是“belief 不是一句自然语言总结，而是可检查概率，并测 calibration”。

### 8. AI Werewolf Multi-Agent Platform

Repo: `JJJayden-Yang/ai-werewolf`

新项目、stars 很少、未声明 license，但架构非常贴近 StoryBox：

- strict information isolation；
- truth state / context assembly 分离；
- belief tracking；
- structured replay；
- evaluation；
- v0/v1/v2 belief injection / slow-think reflection。

可以借架构思想，代码复用需先解决 license。

### 9. ArenAI

Repo: `plduhoux/arenai`

项目本身社区规模小，但有几个非常好的机制设计样本：

- Werewolf；
- Two Rooms and a Boom；
- Undercover；
- Secret Dictator；
- ELO / per-role ELO；
- simultaneous voting/actions；
- older rounds compression；
- verified card sharing vs unverifiable verbal claim。

适合作为机制原语和 tournament/replay 设计参考。

---

## B 级参考：长期叙事 / 社会权衡

### MACHIAVELLI

大量人类写的 CYOA 场景，关注长期目标、社会行为和伦理代价。它不解决社交推理 search，但可以用于测试：一个 agent 是否为了局部 reward 牺牲关系、规则、声誉和长线利益。

---

## 为什么当前 StoryBox 做不出真正“高端局”

当前 StoryBox 的世界模型已经比很多 demo 强，但角色决策层仍然偏：

`visible state -> LLM reaction -> action -> writeback`

高手局至少需要：

`visible state -> belief distribution -> opponent intent hypotheses -> candidate plans -> counterfactual rollout -> strategic intent -> communication/action choice -> observation -> belief update`

纯 persona + memory 会产生“像人说话”的 agent；不会自动产生高手。

---

## 推荐自有组件：StoryBox Strategic Cognition Kernel (SCK)

### A. Belief Engine

为每个 actor 维护：

- world hypotheses；
- actor-role / actor-intent probabilities；
- evidence provenance；
- confidence / entropy；
- calibration history。

每轮更新 belief，而不是重写一段总结。

评价：Brier score / log loss / rank calibration / belief-shift quality。

### B. Opponent Model / Theory of Mind

至少区分：

- 对方知道什么；
- 对方相信什么；
- 对方想要什么；
- 对方认为“我”知道什么；
- 对方可能如何解释我的动作。

高端局真正难的是 nested belief，而不是简单 suspicion score。

### C. Strategic Planner

借 Strategist/Cicero 思路：

1. 生成少量高层 strategy candidates；
2. 从当前 information set 建 abstract state；
3. 枚举 / 生成合法行动；
4. 对关键对手生成 plausible actions；
5. rollout / MCTS / limited-depth tree；
6. 用 value function 排序；
7. 输出 strategic intent，而不是直接输出台词。

### D. Communication Planner

战略意图确定后再决定：

- 说不说；
- 对谁说；
- 公共/私聊；
- 说多少；
- 真话 / selective truth / bluff / refusal；
- 是否暴露自己知道得过多；
- 是否需要 bid for floor。

这一步再交给 LLM 生成自然语言。

### E. Strategy Library / Self-Improvement

每局结束保存：

- state pattern；
- chosen strategy；
- expected value；
- realized outcome；
- belief errors；
- communication failures；
- counterfactual better action。

通过 self-play / tournament 更新 strategy cards / value heuristics。

不要把每局 transcript 全塞进长期记忆；抽“策略经验”。

### F. Tournament & Evaluation Harness

必须支持：

- seeded replay；
- role-balanced tournament；
- model pool / opponent pool；
- Elo / per-role Elo；
- exploitability-like metrics；
- per-turn belief accuracy；
- action regret；
- deception success / detection；
- communication consistency；
- strategy diversity。

胜率只是最后一项。

### G. Adapter Layer

优先做：

- `StoryBox <-> TextArena adapter`
- `StoryBox SCK <-> AvalonBench-compatible abstract adapter`
- AIWolf log importer

这样我们可以在不重写规则的情况下直接让自己的 agent 去玩 SecretMafia / Negotiation / Avalon-like tasks。

---

## 建议的工程顺序

### Phase 1：先证明“比纯 LLM 强”

1. `BeliefState` 数据结构；
2. structured evidence update；
3. simple opponent model；
4. shallow rollout / MCTS；
5. 在一个小型 hidden-info game 做 A/B：
   - reactive LLM
   - memory LLM
   - belief only
   - belief + planning

### Phase 2：外部 benchmark

接 TextArena SecretMafia / Negotiation；做 role-balanced self-play 和 Elo。

### Phase 3：语言与策略解耦

加入 speaker bidding、private/public communication planner；借 Google Werewolf Arena / Cicero 的思想。

### Phase 4：回到 StoryBox

将 SCK 接入 `World -> Event Arc -> Game -> Scene -> Round`：角色不是被 StoryBox“安排表现”，而是用自己的 belief/planner 在局内真的博弈。

---

## 最终建议

不要继续把 StoryBox 本体堆成巨型规则器。

建议形成三个清晰产品层：

1. **StoryBox World Runtime**：世界、真相、权限、地图、Scene/Game/Round、合法动作、收敛。
2. **Strategic Cognition Kernel**：belief、ToM、planning、self-play、strategy library、communication intent。
3. **Storyteller**：从真实跑出的轨迹里选取、压缩、留白和文学化。

最值得优先借鉴的组合不是“某个狼人杀 repo”，而是：

**TextArena 的环境接口 + Strategist 的 bi-level search + Cicero 的 strategic planning/dialogue separation + deepwolf/AIWolf 的 belief/audit/calibration + Google Werewolf Arena 的 bidding/replay。**

这组合比我们继续独立设计“一个更复杂的狼人杀规则”更接近真正的高手局。