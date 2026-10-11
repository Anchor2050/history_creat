# StoryBox Strategic Cognition Kernel v1

状态：设计稿，尚未实现。

## 目标

为 StoryBox 提供独立的“高手局认知组件”。

StoryBox 负责：真相、世界、权限、地图、资源、合法动作、Scene/Game/Round、action collision、writeback、收敛。

SCK 负责：角色在自己可见信息下如何形成信念、预测别人、规划、多步推演、选择战略动作和沟通意图。

Storyteller 负责：把已经发生的轨迹渲染成小说。

严格禁止 SCK 读取 StoryBox backstage truth。

---

## 输入接口

```python
StrategicObservation(
    actor_id,
    game_id,
    scene_id,
    round_no,
    visible_public_state,
    visible_private_state,
    legal_actions,
    reachable_contacts,
    game_local_role,
    game_local_stake,
    game_local_authority,
    commitments,
    reputation,
    fatigue,
    resources,
    cross_game_portfolio_summary,
    observation_history,
)
```

所有输入必须由 StoryBox visibility layer 生成。

---

## 核心状态

### 1. BeliefState

```python
BeliefState(
    hypotheses,
    actor_role_probs,
    actor_intent_probs,
    evidence_links,
    entropy,
    confidence,
    last_update,
)
```

要求：

- 概率和证据来源可审计；
- 新证据更新而非覆盖；
- 允许冲突证据；
- 记录“为什么改变”；
- 支持 calibration。

### 2. TheoryOfMindState

```python
TheoryOfMindState(
    target_actor,
    believed_private_info,
    believed_goal,
    believed_constraints,
    believed_beliefs_about_me,
    predicted_action_distribution,
)
```

至少支持一层 nested belief；高预算模式可支持二层。

### 3. StrategyState

```python
StrategyState(
    current_strategy,
    alternative_strategies,
    intended_public_signal,
    intended_private_signal,
    protected_information,
    commitment_budget,
    risk_budget,
)
```

---

## 决策流水线

### Stage A: Observation normalization

把原始 Scene/Round state 压成 agent 自己的 information set。

### Stage B: Belief update

输入：新公共事件、私有消息、动作、投票、资源变化、沉默、时间延迟。

输出：更新后的概率与 evidence graph。

### Stage C: Opponent-model update

为最相关的若干 actor 维护 intent / capability / likely next action 分布。

避免对所有 NPC 做昂贵 nested ToM。

### Stage D: Strategy candidate generation

由 LLM 或策略库生成 3–8 个高层策略，例如：

- 公开要求冻结决定，私下继续查证；
- 暂时接受对方叙事，保存反证；
- 主动承担一部分责任换取信息权限；
- 沉默一轮，观察投票/站队；
- 拉一个可信第三方验证。

策略不是台词。

### Stage E: Counterfactual planner

对候选策略进行有限深度 rollout：

1. 生成对手 plausible responses；
2. 模拟 StoryBox abstract transition；
3. 计算 value distribution；
4. 考虑不同隐藏世界 hypothesis；
5. 保留 robust / risk-aware strategy。

Planner backend：

- baseline: depth-1/2 heuristic rollout；
- advanced: MCTS；
- expert: bi-level strategy search（参考 Strategist 思路重实现）。

### Stage F: Action intent selection

产出结构化决策：

```python
StrategicDecision(
    chosen_action,
    target,
    strategic_intent,
    expected_value,
    uncertainty,
    protected_information,
    desired_reader_irrelevant=False,
)
```

### Stage G: Communication planner

只有需要语言时才运行。

输出：

```python
CommunicationIntent(
    channel,
    audience,
    speech_act,
    disclosure_level,
    claim_set,
    omitted_facts,
    bluff_or_selective_truth,
    tone_constraints,
    floor_bid,
)
```

然后再由语言模型生成自然语言。

**禁止自然语言模型直接决定战略动作。**

---

## Multi-Game 支持

角色可同时参与多个 Game。

SCK 接受 portfolio summary，但各 Game belief/role/stake 独立。

跨 Game 可共享：

- fatigue；
- general reputation；
- commitments；
- learned strategy；
- persistent relationships。

跨 Game 不自动共享：

- confidential evidence；
- game-local beliefs；
- local authority；
- hidden role。

一个人在 Game A 合作、Game B 阻挠是合法的，只要局部利益和可见信息支持。

---

## 自我进化

### Post-game review

每个 Game 结束后生成：

```python
StrategyReview(
    key_decisions,
    belief_errors,
    action_regret,
    communication_failures,
    successful_signals,
    exploitable_patterns,
    counterfactual_actions,
)
```

### Strategy library

长期保存抽象策略，不保存完整逐字 transcript。

每条 strategy card：

- trigger pattern；
- applicable roles/stakes；
- recommended strategy；
- failure modes；
- evidence count；
- expected value；
- confidence；
- opponent types where it fails。

### Self-play

支持：

- mirror self-play；
- frozen-opponent pool；
- mixed-model league；
- curriculum games；
- adversarial exploit search。

---

## 评价体系

### Game outcome

- win rate / utility；
- per-role Elo；
- faction-conditioned result。

### Belief quality

- Brier score；
- log loss；
- calibration curve；
- belief shift after informative evidence；
- resistance to non-informative accusation。

### Strategic quality

- action regret；
- expected value vs chosen value；
- robustness across hidden-world samples；
- strategy diversity；
- exploitability / repeated-pattern vulnerability。

### Communication quality

- consistency between speech and game action；
- deception success；
- deception detection；
- unnecessary information leakage；
- persuasive effect on target belief/action；
- reputation cost。

### Long-world quality

- cross-game commitment violations；
- reputation drift；
- fatigue-induced decision degradation；
- relationship damage vs local utility。

---

## 外部环境 Adapter

### TextArenaAdapter

目标：把 SCK agent 放进 TextArena 现成环境。

转换：

`TextArena observation -> StrategicObservation`

`StrategicDecision -> TextArena action`

首批 benchmark：

- SecretMafia；
- Negotiation；
- Diplomacy；
- TwoRoomsAndABoom / comparable hidden-info environment。

### AvalonLikeAdapter

不直接复用 Avalon-LLM 代码，按论文概念实现：

- information set；
- legal action enumeration；
- hidden-role belief；
- proposal/vote/mission/action phases；
- strategy rollout。

### AIWolfLogAdapter

读取公开比赛 log，重放 agent 在每一步原本可见的信息，用于 offline belief/action evaluation。

---

## 实现优先级

### v0

- `BeliefState`
- evidence ledger
- heuristic belief update
- structured strategic decision
- replay/evaluation

### v1

- simple opponent model
- 2-ply rollout
- communication intent separation
- TextArena adapter

### v2

- MCTS
- strategy library
- self-play league
- Brier/action-regret dashboard

### v3

- bi-level strategy improvement
- nested ToM
- mixed concurrent Game planning
- cross-game resource/commitment optimization

---

## 一条最重要的约束

SCK 的目标不是让每个角色“更聪明地把作者剧情演出来”。

它的目标是：

> 给角色同样的局面、信息和约束，允许它真正在局里做一个有战略价值的决定；StoryBox 接受后果，哪怕这个决定让原本预想的剧情完全失败。

只有这样，自有组件才可能产生真正意义上的高手局。