# Personal / Normal-Abnormal / Storyteller 收敛方案（Pass 07）

## 1. 当前缺口

截至 2028-12-31，`career-six-cohort` 已经有较厚的 hard-world + social interaction ledger：工作、求职、城市、住房、公开程序、失败、候选帮助、弱联系、普通生活都能通过可审计链条推进。但三层仍明显偏薄：

1. **Personal**：人物有事件记忆和 personal scene，但缺少持续更新的“人物如何理解自己经历”的内在状态。
2. **Normal / Abnormal behavior**：当前 replay 主要生成合理行为，尚未显式区分“符合本人基线”与“有因可查的越轨行为”。
3. **Storyteller**：当前还没有把长历史做成只读叙事诊断，更没有系统回答“历史是否已经厚到可以开始小说化”。

原 StoryBox 的三块不能直接照搬。原 Persona 的 `Scratch` 有 innate / learned / currently / lifestyle / daily plan，`reflect.py` 会从记忆生成 thoughts，但 `Persona.step()` 中 reflection 调用被注释。原 abnormal 机制在空闲时按随机 `abnormal_factor` 打开开关，再切换 `_abnormal` prompt；异常 prompt 明确鼓励 out-of-character / strange / dissatisfaction。原 Storyteller 直接通过 `prompt_manager` 从 event DB 生成标题、类型、背景、主题、章节、冲突、plot point 和正文。

本分支保留这些机制的结构价值，但替换模型耦合和不受约束的生成逻辑。

## 2. 统一 cognition backend

新增：

- `narrative/longform/storybox_cognition_protocol_v11.py`

所有语义任务统一成：

```
CognitionTask
  -> task_id
  -> kind
  -> instruction
  -> payload
  -> output_schema
  -> evidence_refs

CognitionResult
  -> same task_id / kind
  -> backend
  -> structured result
  -> evidence_refs actually used
```

支持四类 backend 名称：

- `chatgpt_product_conversation`
- `deepseek_api`
- `local_model`
- `deterministic_control`

**当前默认：ChatGPT 产品对话。** 仓库自己不调用 OpenAI API。ChatGPT 读取 GitHub task，在当前对话中完成 cognition，再把结构化 result 写回 GitHub。

**DeepSeek：** 已有 `narrative.providers.DeepSeek` 提供 `json(instruction, state)`；可以直接接 `run_with_json_provider(...)`。

**本地模型：** 只要提供相同的 `json(instruction, state)` 适配器即可，不改变 Personal / Behavior / Storyteller schema。后续可单独加 Ollama 或 OpenAI-compatible localhost adapter。

## 3. Personal：证据化人物内在状态

新增：

- `narrative/longform/storybox_personal_v11.py`

Personal 不等于作者替人物写心理小说。它只从人物本人拥有的 evidence 生成候选：

- `current_concerns`
- `private_goals`
- `unresolved_tensions`
- `routine_preferences`
- `interpretations`
- `attention_priorities`
- continuity：什么持续、什么改变
- unknowns：现有历史不足以判断什么

每一个非空 Personal item 必须有 `evidence_refs`，并标 `low / medium / high` confidence。

### 硬规则

Personal 层不能直接产生：

- 钱 / 收入变化
- offer / 工作
- 项目
- 推荐
- 新关系
- 论文 / 定理 / 署名
- 健康事实
- 家庭事实

它只能改变后续 cognition 的**注意力、解释和行为倾向**。任何外部后果仍要经过正常 event -> candidate -> feasibility -> writeback 链。

### 推荐节奏

- 普通季度：每人至多一次 Personal snapshot；没有新证据可不更新。
- 强事件后：毕业、落选、换城、入职、明显关系冲突、家庭事件、重要研究失败后，可追加一次局部 reflection。
- 不要求 14 人同频更新。

## 4. Normal / Abnormal：相对本人基线的行为偏离

新增：

- `narrative/longform/storybox_behavior_v11.py`

保留原 StoryBox 的二分字段：

- `mode = normal`
- `mode = abnormal`

但重新定义 abnormal：

> **abnormal = 相对这个人物自己已经形成的行为基线的一次有证据触发的偏离。**

它不表示精神疾病，不要求奇怪、夸张或戏剧化。

例如：

- 平时总接活的人第一次明确拒绝；
- 一直回避冲突的人突然直接说明边界；
- 长期只考一个路线的人因连续失败第一次投另一类岗位；
- 平时谨慎的人在罕见机会窗口中临时决定去见一个人；
- 一直愿意参加聚会的人因疲惫突然提前离场。

### abnormal 必须满足

1. 先写 `baseline_expected_action`；
2. 明确 `deviation`；
3. 有 trigger type：pressure / shock / value conflict / rupture / rare opportunity / exhaustion / deliberate experiment；
4. trigger 必须引用已有 evidence；
5. chosen action 必须在 hard-world 提供的 feasible actions 里；
6. 每人每个时期有 abnormal budget，默认很低；
7. abnormal 不能创造人物不知道的信息、没有的钱、没有的权限、没有的关系或不可能的物理移动。

因此异常行为会稀有且有后果，不会成为“随机发疯按钮”。

## 5. Storyteller：先做只读史料编辑器

新增：

- `narrative/longform/storybox_storyteller_v11.py`

当前阶段 **不让 Storyteller 写小说正文，更不让 Storyteller 反写历史**。

Storyteller 只读 ledger + Personal snapshots，输出：

- recurring conflicts
- causal chains
- protagonist candidates + counterargument
- scene clusters
- underrepresented lives
- competing interpretations
- history thickness diagnostic
- `continue_history | ready_for_literary_experiment`

每一条冲突、人物弧、场景候选必须引用 event IDs。Storyteller 可以说“有两种解释”，不能补一个历史里没有发生的场景。

### history thickness

新增 deterministic diagnostic，检查：

- 14 人覆盖度
- 时间跨度
- candidate lifecycle 数量
- 重复关系链
- 普通生活密度
- 失败 / 关闭 / 反例密度

它只是工程诊断，不是文学质量分。即使达到 `substantial`，也只意味着“可以开始试做文学层”，不意味着故事自动好看。

## 6. 运行方式

### A. 当前 ChatGPT 产品对话（现在就能用）

每次从 `head-v2.json` 物化当前世界后：

1. 生成本批次 social/hard-world micro windows；
2. 对关键人物生成 Personal task；
3. 当前 ChatGPT 在本对话里完成 Personal result；
4. 每个关键行为先过 Behavior task，判 normal/abnormal；
5. 执行合法事件并写 ledger；
6. 季度/年度结束跑一次 read-only Storyteller diagnostic；
7. Storyteller 结果另存，不改变历史。

### B. DeepSeek API

使用同一 task，交给 `narrative.providers.DeepSeek.json(...)`。结果仍经过同一 validator；DeepSeek 没有更高世界权限。

### C. 本地模型

实现一个提供：

```python
provider.json(instruction, state) -> dict
```

的适配器即可。Ollama / llama.cpp / OpenAI-compatible localhost 都可以在这一层接，不需要复制人物、行为或 Storyteller 逻辑。

## 7. 存储建议

继续 append-only：

```
runtime/chatbot-live/
  batches/
  personal/
    2029-q1.json
    ...
  storyteller/
    2028-diagnostic.json
    2029-diagnostic.json
  behavior-audit/
    2029-q1.json
  head-v2.json
```

Personal 和 Storyteller 永远不覆盖历史 batch。

## 8. 2029 起的主循环

从当前 `2029-01 高原第一份工作` 起，每个季度执行：

```
materialize history
  -> refresh Personal only where evidence changed
  -> generate feasible social/hard-world windows
  -> behavior routing (normal by default; abnormal must be earned)
  -> current ChatGPT cognition
  -> event execution
  -> candidate feasibility
  -> append batch
  -> update Personal
  -> quarterly behavior audit
  -> annual Storyteller diagnostic
```

2029 的 Storyteller 仍是诊断模式，不写小说。等底层历史、Personal continuity 和行为偏离链都足够厚，再单独打开 literary mode。

## 9. 测试

新增 `tests/test_storybox_personal_behavior_storyteller_v11.py`，锁住：

- Personal 每个非空判断必须有 evidence；
- Personal 不得直接写 hard-world；
- abnormal 必须有 trigger + baseline deviation；
- abnormal 不能选择 feasibility 之外的 action；
- abnormal budget 防止戏剧膨胀；
- Storyteller 必须引用历史 evidence；
- Storyteller 永远 read-only。

当前通过 GitHub connector 完成代码提交，未在完整 checkout 中执行 pytest，因此不能声称测试已通过。
