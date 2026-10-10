> 历史文档：仅描述最早的因果原型。当前功能与限制请看 [新版说明](narrative-v1.md) 和 [验证报告](validation-v1.md)。

# 第一阶段：因果推演核心

这是与原版 StoryBox 并存的实验入口：借用“观察 → 决策 → 行动 → 历史 → 写作”流程，把世界结果从自由文本生成中分离出来。原版 reverie/ 和依赖配置保持不变，暂未把新核心接入旧的 Persona/Storyteller。

## 运行条件

新入口仅需 Python 3.11+ 标准库，本机已用 Python 3.13.5 验证。不需要 uv sync、GPU、嵌入模型或 OpenAI 账户。原版的 Python/依赖要求仍按原 README。

在项目目录执行：

```powershell
python -m unittest discover -s tests -v
python -m narrative.run
```

默认是明确标注的离线脚本场景，不调用任何 API，也不代表角色自主推演。它验证消息传递、承诺与物品转交等机制。

## 使用 DeepSeek

仅需在本机设置 DEEPSEEK_API_KEY；不要把密钥提交到 Git。程序自动读取项目根目录的本地 .env（已被 Git 忽略）；进程环境变量优先于本地配置。配置解析仅支持这三个 DeepSeek 字段的单行 KEY=VALUE 格式，可使用成对引号，不执行插值或脚本。

```powershell
# 安全输入，不把密钥字面值写入命令历史
$deepseekSecret = Read-Host 'DeepSeek API key' -AsSecureString
$env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $deepseekSecret).Password
$env:DEEPSEEK_MODEL = 'deepseek-flash'
python -m narrative.run --live --steps 6 --max-calls 15 --write-story
```

模型名和 DEEPSEEK_BASE_URL 可替换；默认地址 https://api.deepseek.com。官方接口参考：https://api-docs.deepseek.com/ 。模型默认值依据 2026-10-11 查询的文档；使用账户实际可用模型。兼容 OpenAI 格式不意味着调用 GPT。

每个有效候选通常调用两次：提出行动、判断人物合理性。正文草稿另一次。max-calls 是本次进程的请求次数上限，不是金额上限；每次输出限制 2000 token。没有自动重试，避免意外重复计费；接口错误停止，保留已完成历史。长篇上下文压缩尚未实现。

## 输出和恢复

每次默认使用不同的 output/core-* 目录：

- checkpoint.json：世界状态、带状态变化的完整事件记录，可恢复。
- history.md：便于阅读的事件摘要。
- attempts.jsonl：每次尝试、判断结果、拒绝或故障。被拒绝动作不改变世界，也不推进时间。
- usage.json：本进程请求数和服务端报告的 token 用量；恢复后重新计数。
- story-draft.json / story-draft.md：仅在 live + write-story 时生成，场景带引用事件编号。编号检查不等于语义忠实，草稿需要人工审阅。

```powershell
python -m narrative.run --live --resume output/你的运行目录/checkpoint.json --steps 6
```

恢复默认导出到新目录，适合保留原记录。也可显式指定 --output 到原目录以继续保存；已有运行目录在非恢复模式下拒绝覆盖。不要同时向同一目录运行多个进程。

## 第一版已经实现

- move / transfer / tell / promise / wait 五类动作。硬规则先验证，模型判断不能覆盖所有权、距离、已知信息等约束。
- 每个成功动作推进一个抽象时刻，非真实小时；相邻地点移动占一个时刻。
- 角色输入只有自己的设定、目标、已知事实、持有物品、在场人物、可见历史和相关承诺。
- tell 只允许传播已知事实且双方同地。第一版还没有谎言、可信度、消息延迟和旁观者窃听。
- promise 专指在期限内转交某物；只向当事人展示，履行或逾期改变状态。到期时刻内的转交优先于逾期判断。
- 事件保存动作、可选的已观察前因、状态前后变化。完整历史只供保存和写作，不送给角色。
- DeepSeek 同时负责行动提议和软判断。Judge 的 optional 参数可注入另一个判断实现；失败或输出不合规时回退 DeepSeek，记录异常类型，不记录原始异常文本。

## Jev 的状态

暂不实现真实 Jev HTTP 适配器，也不要求 Jev 密钥。预留协议：对象实现 evaluate(view, action)，返回 {acceptable: bool, reason: str}。未来接入时负责把 Jev 的选择/概率转成经验证的判断结果；不会直接把其置信度当作角色行为概率。回退路径有离线测试。

## 能力边界及下一步

本版是机制原型，不是通用长篇创作引擎。事实表目前全是真实陈述，人物只拥有其中一部分；没有错误信念、组织制度、战斗、生产、人格演化或复杂时间尺度。已保留 traits/goals，但人物差异需要实际模型实验验证。

历史采用 JSON 快照和顶层状态差异，方便检查，规模大后需迁移增量存储。恢复不保证重新请求模型得到相同选择。密钥不写入快照；历史中包含完整人物设定，属于作者数据。

后续优先顺序：真实 DeepSeek 小样本 → 检查人物差异和硬规则拒绝率 → 补对话、认知与因果链 → 组织/制度与长期目标 → 叙事筛选及原版对照。未验证故事质量前不扩大角色数或盲目批量调用。

## 验证记录

已通过 18 项离线测试，覆盖所有权与失败原子性、信息隔离、事件引用、承诺、快照恢复、可选判断回退、请求预算、模型响应错误、轮流行动、故障保存与草稿导出。

2026-10-11 真实 DeepSeek 接口已成功返回人物决策及判断；一次三步试运行中有一个提议被拒绝，两个等待动作提交成功，随后草稿响应解析失败。真实端到端创作尚未通过。Jev API 未调用；原版重依赖流程未执行。
