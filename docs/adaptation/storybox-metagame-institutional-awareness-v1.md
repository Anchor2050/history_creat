# StoryBox Meta-Game / Institutional Awareness v1

状态：架构登记，暂缓实现。当前 SCK falsification gate 优先级更高。

## 为什么需要这一层

现实中的参与者经常知道自己正在“被观察、被评估、被筛选、被记录、被规则约束”。他们不只推理其他参与者，也会推理：

- 谁设计了当前规则；
- 为什么问题被这样提出；
- 谁会收集和阅读自己的行为；
- 明面指标和真实评价函数是否一致；
- 哪些行为是为了实际结果，哪些行为是为了展示；
- 观察者是否知道自己正在被反向揣测；
- 当前局的结果会不会改变下一轮规则。

因此 StoryBox 的现实社会博弈不能只借狼人杀/Avalon 的 hidden-role 模型。还需要 meta-game、principal-agent、strategic signalling、Goodhart-style metric gaming、institutional adaptation 和 repeated-game reputation。

---

## 核心分层

一个角色在某个 Game 中至少可拥有四类目标：

1. **actual_goal**：角色真正希望发生的结果。
2. **stated_rule_goal**：制度/规则公开宣称鼓励的结果。
3. **inferred_evaluation_goal**：角色推测真正掌握评价权的人在乎什么。
4. **display_strategy**：角色决定让观察者看到怎样的自己。

这四者可以一致，也可以部分冲突。

禁止给角色加固定的“虚伪/真诚”全局标签。展示策略必须由当前情境、权力关系、长期声誉、风险和信息支持。

---

## MetaGameState

建议未来 SCK 增加局部状态：

```python
MetaGameState(
    game_awareness,
    inferred_game_purpose,
    rule_designer_model,
    evaluator_models,
    visible_metrics,
    inferred_latent_metrics,
    believed_data_collector_intent,
    believed_observer_beliefs_about_me,
    display_strategy,
    protected_private_goal,
    rule_change_expectation,
    institutional_memory,
)
```

其中 `game_awareness` 不是布尔值。角色可能：

- 完全没意识到自己正在被评估；
- 知道有考核，但猜错评价函数；
- 准确识别规则与真实评价的偏差；
- 意识到观察者也知道自己会“配合演”；
- 进一步尝试利用信誉、顺从或公开承诺改变后续规则。

---

## Action 分解

未来高阶场景中可区分：

- `world_action`：真正改变现实状态的行动；
- `display_action`：专门给观察者看的行动或表述；
- `reported_action`：进入记录、汇报、表格或档案的版本；
- `private_intent`：角色不愿公开的目标；
- `meta_signal`：角色故意释放的“我理解规则/我愿意配合/我不会越界”等信号。

三者不必相同，但任何差异都必须有成本和风险。

---

## Observer / Institution

观察者可以是普通 actor，也可以是制度节点：

- 面试官；
- 导师；
- 领导；
- 评审委员会；
- 项目办公室；
- 人事系统；
- 绩效指标；
- 平台算法；
- 家庭中的实际决策者。

观察者本身也可有局部目标，并且可能同时是：

- 规则执行者；
- 资源分配者；
- 未来合作方；
- 被上级评价的人。

因此主持人/规则制定者不能被默认成中立。

---

## Rule Adaptation

现实中的局会反过来改变规则。

允许：

`Game outcome -> observer belief/reputation -> institutional response -> next-game rules`。

例如：

- 一个人长期表现可靠，获得更大自主权限；
- 团队频繁钻指标漏洞，下一轮考核增加复核；
- 一次公开冲突改变以后谁必须签字；
- 某人长期“配合演戏”建立信用，关键时刻用这份信用推动例外。

规则变化必须通过世界中的权力节点发生，不能由 Storyteller 为了剧情便利直接改。

---

## 与 StoryBox / SCK / Storyteller 的边界

### StoryBox

负责：

- 谁拥有评价权/规则权；
- 哪些指标公开；
- 哪些信息会被记录；
- 哪些行为真的改变制度状态；
- reputation / authority / institutional memory 的 writeback；
- 后续规则变化。

### SCK

负责：

- 推断规则制定者/评价者意图；
- 区分实际目标和展示策略；
- 评估 metric gaming / signalling / compliance 的收益和长期代价；
- 推演“观察者知道我在表演”后的二阶反应；
- 决定是否尝试改变规则。

### Storyteller

只渲染已经发生的行为和后果。

禁止把 `MetaGameState` 直接解释给读者。优先通过具体细节显示，例如：

- 面试者发现某类回答会让对方开始记笔记，于是后面改变答法；
- 正式群里说一套，走廊里补一句；
- 项目负责人问“这句话你准备怎么写进说明”；
- 某人先把表格填到合规，再私下解决真正的问题；
- 一个角色看见考核表后才理解为什么所有人突然开始做同一种事。

---

## 小说使用原则

这层不应该让所有角色都变成算计型高手。

保留差异：

- 有人根本不擅长揣测评价体系；
- 有人能看懂规则但不愿表演；
- 有人很会展示，却判断错了真正权力结构；
- 有人短期玩得漂亮，长期声誉受损；
- 有人习惯守规则，反而在关键节点获得高信任；
- 高影响力角色更可能同时处在“玩家 + 观察者 + 被观察者”三个位置。

精彩来自这些差异及其后果，不来自人人都会三层反向推理。

---

## 在《不同的稳定》中的自然入口

适合出现于已有生活线，而无需制造阴谋：

- 求职/面试：回答问题，同时推断筛选逻辑；
- 高校行政/研究支持：合规文本、真实需求、责任记录三者错位；
- 国企技术岗位：公开风险结论与领导真正需要的可执行承诺之间的张力；
- 医药统计：分析结论、客户希望听到的结论、监管可接受表述之间的差异；
- 学术合作：真正想证明什么、能投稿什么、导师/审稿人会如何读取证据；
- 家庭决策：表面讨论房子/工作，实际在测试承诺、距离、稳定性和未来责任。

---

## 当前执行决策

此层仅登记，不阻塞当前 SCK 主线。

当前最高优先级仍是 message bus 0016 规定的：

1. native `[N]` public-vote visibility；
2. paired cross-play；
3. replay-calibrated evidence model；
4. held-out evaluation；
5. 保持 MCTS / StoryBox reconnection 冻结。

只有当前 SCK falsification gate 完成后，才考虑实现 `MetaGameState` 或把它接入和平 mixed-motive benchmark。
