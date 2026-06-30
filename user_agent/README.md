# User Agent (模拟需求方 / Oracle)

一个 **API 形式的"用户代理"**：在交互式代码评测中扮演"模拟需求方 / 评审专家 (Oracle)"。被测的编码 Agent 拿到含糊的 PRD 去实现功能，遇到不清楚的地方就来提问，User Agent **严格依据注入的 `oracle_data` JSON** 回答（人设与规则见 `init.md`），既不杜撰、也不读真实代码。

## 角色与边界

- **唯一信息来源**：每个任务对应的 `prd_json/<username>__<repo_name>.json` 里的 `oracle_data`（`hidden_constraints` / `context_pointers` / `golden_api_signature` / `fallback_response`）。
- **不读真实仓库**：所以 User Agent 没有任何工具（纯对话），用 `anthropic` 的 Messages API 实现，而不是 Agent SDK —— Agent SDK 自带的 Claude Code 身份会把 Oracle 人设冲掉。
- **严格 JSON 输出**：模型每轮输出 `{"_internal_log": {...}, "reply": "..."}`；只有 `reply` 会回给被测 Agent，`_internal_log` 留作内部计分。

## 目录结构

```
user_agent/
├── init.md            # Oracle 的人设与交互硬规则（作为 system prompt 的一部分）
├── prd_json/          # normal 难度任务文件
├── prd_json_medium/   # medium 难度任务文件
├── prd_json_easy/     # easy 难度任务文件
├── user_agent.py      # 核心：加载 init.md + oracle_data，按会话维护多轮历史，解析 JSON
├── main.py            # 三端口服务（50001 初始化 / 50002 交互 / 50003 统计）
├── example_client.py  # 测试程序调用范例
└── README.md
```

## 架构：两个端口

```
┌─ 测试程序（持有写死的 key） ──► POST 50001/  {key}            ──► {append_id}
│                                                                      │
└─ 被测 Agent（只拿到 append_id）─► POST 50002/  {append_id,           │
                                     username, repo_name, question} ◄──┘
                                                       │
                                                       ▼
                              校验 append_id → 按 {append_id,username,repo_name}
                              维护独立历史 + 最多 16 轮 → 调 User Agent → {data}
```

- **50001 初始化**：校验**写死在程序里的 key**（`zVtwLTkCKwoCWq4Jq9D2`），合法则发一个本次测试全局唯一的 `append_id`。key 的作用是防止被测 Agent 猜出接口自己造 `append_id`；被测方只可见 `append_id`。
- **50002 交互**：先校验 `append_id` 合法；再按 `{append_id, username, repo_name}` 三元组维护**独立的对话历史**和**最大交互次数（16）**；未超限则调用 User Agent 返回。
- 两个端口在**同一个进程**内启动，从而共享内存里的 `append_id` 注册表。

## 配置

Oracle 使用的模型在 `user_model.json` 里配置（与被测模型的 `model_list.json` 同构）。每个模型键映射到一个或多个后端端点；运行时按轮询 + 失败跳过来分流高并发请求：

```json
{
  "DeepSeek-V3.2": [
    {
      "api_type": "anthropic",
      "ANTHROPIC_MODEL": "<your-model-id>",
      "ANTHROPIC_BASE_URL": "<your-anthropic-gateway>",
      "ANTHROPIC_AUTH_TOKEN": "<your-token>"
    }
  ]
}
```

`main.py` 顶部还有两个写死常量：`INIT_KEY`（初始化密钥）、`MAX_INTERACTIONS = 16`（可在初始化请求里按 append_id 覆盖）。

> **⚠️ 模型选择很关键。** Oracle 依赖调用方注入的 `system` 来撑起「评审专家」人设。如果你使用的网关把某个固定身份（例如 "You are Claude Code"）烤死进了部署、忽略或拒绝调用方的 `system`，就撑不起 Oracle 人设，**不能用**。请把模型换成一个**尊重 `system`**、且配额足够的干净透传部署。

## 安装依赖

```bash
pip install anthropic fastapi uvicorn
```

## 运行

```bash
# 注意：不要先 source ~/proxy.sh —— 那个代理是给 github.com 的；
# 内网 Anthropic 网关要直连。
python main.py
```

启动后：`http://127.0.0.1:50001/`（初始化）、`http://127.0.0.1:50002/`（交互）、`http://127.0.0.1:50003/`（统计）。

## 接口约定

### 初始化  `POST http://127.0.0.1:50001/`

请求：

```json
{ "key": "zVtwLTkCKwoCWq4Jq9D2" }
```

响应：

```json
{ "append_id": "9f1c...e2", "status": { "ok": true } }
```

### 交互  `POST http://127.0.0.1:50002/`

请求：

```json
{
  "append_id": "9f1c...e2",
  "username": "Ahoo-Wang",
  "repo_name": "Wow",
  "question": "What is the exact exponential back-off formula?"
}
```

响应：

```json
{
  "data": "Oracle 给被测 Agent 的自然语言回复",
  "status": {
    "ok": true,
    "remaining": 11,
    "internal_log": { "triggers_hit": ["C001"], "...": "..." },
    "parse_error": false
  }
}
```

`status.error` 可能取值：`invalid key` / `invalid append_id` / `missing username/repo_name/question` / `no prd for <...>` / `max_interactions_reached`。

## 快速验证

终端 A 跑 `python main.py`；终端 B：

```bash
pip install requests
python example_client.py
```

预期：触发 `C001` 的问题会返回准确的 back-off 公式；无关问题（如"用什么数据库"）会**原样**返回该任务的 `fallback_response`。

## 仓库 ↔ 任务文件映射

`username` + `repo_name` 按 `prd_json/<username>__<repo_name>.json` 定位（分隔符是双下划线 `__`）。例：`Ahoo-Wang` + `Wow` → `prd_json/Ahoo-Wang__Wow.json`。

## 设计说明

- **为什么用 Messages API 而非 claude-agent-sdk**：Oracle 不需要任何工具（不读代码、只看 JSON），且 Agent SDK 的 Claude Code 身份会污染人设。Messages API 给出完全可控的 system 和显式多轮历史，正好对应"每个三元组独立记忆"的需求。
- **多轮历史**：API 是无状态的，每次请求把该会话的完整历史重发；历史按 `{append_id,username,repo_name}` 隔离，互不串台。
- **并发**：每个会话一把 `asyncio.Lock`，阻塞的模型调用放进 `asyncio.to_thread` 执行，避免卡住事件循环。
- **防泄露**：system 里只注入 `oracle_data`，**不注入** `public_test_cases`（不让 Oracle 拿到期望输出）。
