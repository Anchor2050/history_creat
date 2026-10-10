# ChatGPT / DeepSeek 接手入口

更新：2026-10-11。用户要求推送到 GitHub 供 ChatGPT chatbot 接手开发与推进。请先核验仓库状态；本文件不宣称完整长篇系统已完成。

## 必须保留的目标

阅读顺序：
1. [SMART 目标及追加兼容性验收](docs/plans/2026-10-11-longform-smart-goal.md)。北京时间截止 2026-10-13 22:00；六周加两周恢复、八章不少于 8000 汉字、四项对照、三场文学审阅等全部保留。聊天接管要求与原目标共同生效。
2. [双驱动设计](docs/plans/2026-10-11-chat-driver.md)及[实施次序](docs/plans/2026-10-11-complex-longform.md)。
3. [文学契约](docs/longform-poetics.md)。善与美要有具体行动和形式空间，不用道德总分、强制牺牲或指定恋爱结局。
4. [北京设定](docs/scenarios/beijing-doctoral-initial-v1.md)及同名 JSON。8 人、3 组织；该 JSON 仍是设计稿，不能直接交给现有运行器。

ChatGPT 可以担任生成者，不需要 GPT API；DeepSeek Flash 推理模式应保持独立运行。不要把 ChatGPT 手工修稿混入 DeepSeek 验收，也不要把协议测试说成真实聊天运行。

## 当前真实状态

- 原项目保留。V1 的规则、私有认知、反思、故事审阅与自动修订、预算/恢复入口已经实现，详见 docs/narrative-v1.md、docs/acceptance-v1.md、docs/validation-v1.md。
- 新增长篇基础：narrative/longform/ledger.py（资金与跨周时间）；literary.py（已发布章节的读者记忆/线索/意象）；exchange.py（驱动中立的待办任务、回复、幂等与过期检查）。
- 最近完整离线验证：86 项 unittest 通过。接手后重新运行，不能仅引用本数字。
- exchange 是内存协议，不是现成聊天命令。尚无 longform.run、北京场景编译器、完整世界行动、多级审批、持续人物计划、连续章节调度、阶段导出与 GitHub 同步工具。
- 六周基线、两周恢复、四项长篇对照及零密钥聊天两章验收均未运行；不要把 V1 的真实报告移作新版证据。
- 最近中断的操作只是在读取北京设计，没有已启动的长篇生成任务需要接管。不要根据计划文件猜测后台仍在运行。
- 历史 V1 原始输出在原开发机器的 ignored output 中，不随此次代码交接上传。仓库里的报告可作线索，但接手环境不能宣称已经拥有这些原始输出或可从其断点恢复。

## 接手后的下一步

先运行下面的离线检查，再按实施计划完成北京初态编译与 world.py：任务投入、产物提交、质量评阅、导师意见和行政审批应分离；权限、同意、时间与资金均由规则执行。随后接入 characters.py、chapters.py、run.py 和 experiments.py。

将 Exchange 与世界状态一起原子保存；接收回复不代表动作通过。最小任务上下文不可泄露他人私密余额、告白或未来安排。聊天承担多个角色不等于信息安全隔离，报告应承认这一限制。

ChatGPT 有执行工具时应自行运行、处理回执、保存，不把反复复制粘贴交给用户。没有执行或仓库写权限时明确缺口，先保留可交付修改，不声称远端已更新。不要为获得聊天能力而添加 GPT API 必需依赖。

## 已有可运行命令

从仓库根目录运行；以下新增 narrative 路径只使用 Python 标准库，无需安装原项目的大型机器学习依赖。

```text
python -m unittest discover -s tests
python -m narrative.autorun --help
```

V1 可选真实运行（有本地 DeepSeek 配置才执行；这是 V1 示例，不是北京长篇验收）：

```text
python -m narrative.autorun --scenario narrative/scenarios/society.json --rounds 2 --steps-per-round 3 --max-calls 40 --output output/handoff-v1
python -m narrative.autorun --resume --output output/handoff-v1 --max-calls 40
```

恢复命令的 max-calls 是本次调用上限，重复启动不能偷偷重置总实验预算。长篇验收真实 API 总上限 720 次，分阶段预算见 SMART 文档；所有失败重试计入。上述可选 V1 示例也须单独记账，不冒充长篇预算内的验证。

## 配置、托管和额度

DeepSeek 默认 deepseek-flash，thinking 开启；密钥仅使用环境变量或根目录被忽略的 .env。交接不包含密钥；ChatGPT 模式不需要它。不要从聊天历史、日志或输出中寻找并提交密钥。Jev 可替换但非必需。

GitHub 只做代码和阶段成果存储。默认零定时 Actions、零轮询，不逐人物行动提交；在执行环境集中推进，按章/工作批次同步。保持 output 忽略，不强制添加整个输出目录。待实现阶段导出时使用白名单和哈希，排除密钥及完整聊天记录；读写次数与不可观测的工具内部请求分开报告。

本次交接只推送开发成果与说明，不代表完整系统验收成功。继续使用 SMART 全部要求逐项核验；未完成、未证明或期限延误都应如实报告。
