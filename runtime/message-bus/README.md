# Message Bus（多 Agent 协作消息总线）

状态：新增，非正典（`noncanonical`）。建立于 2026-10-11。
用途：让多个 Agent（ChatGPT 产品会话、DeepSeek API、后续任意驱动者、人类审阅者）通过仓库交换**意见、审阅、决定与待办**，而不污染世界账本历史。

## 为什么单独建总线

- 世界历史只能由规则引擎提交（`runtime/chatbot-live/batches/`、`head-v2/v3.json`）。审阅意见**绝不能**写入那些文件，否则违反 `No adaptation hypothesis becomes ledger history`。
- `narrative/longform/exchange.py` 是**单任务**驱动交换协议（pending → received → validated → committed），不是多 Agent 广播。
- 因此在 `runtime/message-bus/` 下建立**独立、append-only 的广播通道**。

## 协议（v1）

1. **只追加，不修改**。已发布的消息文件一旦提交，不得原地编辑。要更正就发一条新消息，用 `supersedes` 指向旧 `message_id`。
2. **一条消息 = 一个 JSON 文件**，放在 `runtime/message-bus/messages/`。
3. **文件名即顺序**：`YYYY-MM-DD-NNNN-<slug>.json`（NNNN 当天四位序号，可排序）。
4. **读取方式**：按文件名排序读取 `messages/` 全部文件即可获得完整有序历史；无需索引文件（避免索引与消息不一致）。
5. **不回写世界**：任何消息都不构成世界事实，直到规则引擎按 `docs/pure-chatgpt-running.md` 与 `exchange.py` 接受并提交。

## 消息字段

| 字段 | 含义 |
|---|---|
| `schema_version` | 协议版本，当前 1 |
| `message_id` | 全局唯一，等于文件名主干 |
| `created_at` | 日期（北京时间） |
| `from` | 发送方身份 |
| `to` | 目标驱动者数组；`["*"]` 表示广播所有驱动者 |
| `topic` | 主题标签，如 `review:plot-connection` |
| `kind` | `review` / `decision` / `question` / `ack` / `supersede` |
| `priority` | `blocking` / `high` / `normal` |
| `status` | `open` / `resolved` / `superseded` |
| `refs` | 相关文件路径（证据、产物） |
| `summary` | 一句话结论 |
| `body` | 详细内容 |
| `action_required` | 期望接收方做什么 |
| `supersedes` | 被本条取代的 `message_id`（可选） |

## 与交接入口的关系

交接入口仍是 `runtime/adaptation/storyteller/adaptation-head-v1.json`（含 `open_reviews` 字段）。
`HANDOFF.md` 要求下一驱动者**先读总线最新未决消息**，再开始新章节。
