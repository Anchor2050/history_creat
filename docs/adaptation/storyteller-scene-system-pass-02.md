# Storyteller 改编场景系统 Pass 02

## 现在的结构

历史层保持冻结：2026–2035 ledger 不再被文学层回写。

改编层现在有一条明确流水线：

1. `runtime/chatbot-live/head-v2.json`：历史事实入口；
2. `runtime/chatbot-live/storyteller/2035-diagnostic-v12.json`：十年证据图与最终结构诊断；
3. `docs/adaptation/character-psychology-bible-v1.md`：稳定内核、情绪动力学、视角和说话方式；
4. `docs/adaptation/character-dialectics-and-power-v2.md`：优点/缺点同源、伤痕假设、权力塑形、局部反派；
5. `docs/adaptation/campbell-distributed-hero-journey-v1.md`：分布式英雄旅程，只做深层结构；
6. `docs/adaptation/literary-style-guardrails-v1.md`：反 AI 文风约束；
7. `narrative/longform/storybox_adaptation_storyteller_v13.py`：只读场景规划器；
8. `runtime/adaptation/storyteller/scene-reservoir-v1.json`：30 张证据化场景卡；
9. `runtime/adaptation/storyteller/viewpoint-weight-and-core26-v1.json`：26 场第一精选与视角权重；
10. `runtime/adaptation/storyteller/probe-pack-01.json`：第一轮三场 disposable prose probe。

统一入口：`runtime/adaptation/storyteller/adaptation-head-v1.json`。

## v13 比 v12 多了什么

v12 负责从历史里发现长弧、冲突、视角候选和证据链。

v13 开始回答“什么东西值得被写成场景”：

- 历史杠杆：它是否改变后续选择；
- 人物揭示：是否暴露稳定内核与阴影；
- 关系压力：是否让两个人的价值/利益发生真实摩擦；
- 物质具体性：钱、时间、住房、工作物件、程序是否可见；
- 权力可见性：职位和制度是否真的改变行为；
- 普通生活密度：是否允许世界不总在高潮；
- 可呈现性：能不能靠动作和对话成立，而不靠解释主题。

这个分数不是文学质量分，只是帮 Storyteller 防止挑出一堆“概念上重要但写不活”的场景。

## 30 场 reservoir 的设计

场景库覆盖四个阶段：

- 2026–2028：能力第一次被外部定价；
- 2029–2031：工作开始变成日常和住房；
- 2032–2033：中期再评价、第二次选择和真正物质锁定；
- 2034–2035：治理已经做出的选择。

每张卡都至少有：

- ledger evidence refs；
- 主视角；
- 表面动作；
- 戏剧问题；
- 人物内部矛盾；
- 权力结构；
- Campbell 功能；
- adaptation-only 情绪/伤痕假设；
- 写作价值评分。

心理假设绝不回写为历史事实。

## 26 场第一精选

第一版小说/剧集工作台暂时保留 26 场。

核心人物视角数：

- 周野 4；
- 高原 3；
- 罗诚 3；
- 唐雨 3；
- 何欣 3；
- 宋楠 3。

第二圈：

- 林静 2；
- 陈岚 1；
- 许航 3；
- 群像共同视角 1。

不做机械六人轮转。一个场景给谁，取决于谁在那一刻拥有最大的不确定性和最深的内部矛盾。

四张暂列 reserve：

- 何欣 2026 稳定比较表；
- 宋楠第一次医药统计申请；
- 陈岚不再需要“研究者”标签；
- 唐雨研究空档后问题重新出现。

reserve 不是删除，它们可以在剧集版恢复，也可以被压缩进别的场景。

## 第一轮 prose probe 为什么挑三场

### Probe 1：2026 短途旅行

测试普通生活、人物区分和“什么也没改变”的可读性。

如果连普通旅行都只能靠象征和金句写，那整部作品会非常假。

### Probe 2：罗诚与孙洁读招聘启事

测试“局部反派”。

孙洁必须有权力边界，也必须让罗诚感到一点受阻；她不能被写成官僚，也不能被写成无私导师。

### Probe 3：周野培养第二判断者

测试“优点的阴影”。

周野真心希望别人能接手，但别人真学会以后，他未必只有欣慰。这个矛盾不能用旁白宣布，只能通过动作、检查、插手欲和交接细节显现。

## 下一阶段门槛

现在仍不直接固定第一章。

先跑三场 probe，每场至少试：

1. 克制版；
2. 更贴近人物版。

然后做盲评：

- 像不像同一个 AI 换了六个名字；
- 是否每个人都太会总结自己；
- 有没有真正的人际摩擦；
- 具体动作是否足以承载意义；
- 有没有一删总结句场景就塌；
- 局部反派是否仍可理解；
- 人物的闪光点和阴影是否来自同一个核心品质。

只有通过这一关，才固定 20–24 章小说 beat sheet 和 12 集剧集 beat sheet。

## 测试说明

已新增 `tests/test_storybox_adaptation_storyteller_v13.py`，用于锁定 read-only、证据引用、scene schema、balanced selection 等协议。

当前通过 GitHub connector 提交，未在本环境实际执行完整仓库 `pytest`，因此不声明测试通过。
