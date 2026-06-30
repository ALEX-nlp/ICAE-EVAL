# 评测说明（ICAE-Bench）

基于 `claude-agent-sdk`（Claude Code CLI）或 OpenHands SDK 搭建的交互式代码生成评测平台。被测 Agent 拿到一份**模糊 PRD（fuzzy PRD）**，通过向 User Agent（Oracle）提问澄清需求后，在容器内实现代码；平台再用客观测试 + 结构/语义评估 + 交互质量统计四组指标打分。

> 本发布版的开箱范围：环境为 `base`（仅随附各语言基础镜像），PRD 走 `fuzzy`（Oracle 交互）。

## 实验参数

- `model_name`：从 `model_list.json` 的 "Tested Model" 映射被测模型的端点参数。
- `critic_model_name`（选填，default="Deepseek-V4-Flash"）：用于 Agentic 评估的评审模型，从 `model_list.json` 的 "Critic Model" 映射。
- `eval_mode`：["lite", "full"]。lite 只评测前 50 个仓库（realcode@001–050），full 全量 480。
- `env_mode`：本发布版为 `base`：把 PRD 放进仓库对应编程语言的基础镜像（`docker_lang_official/<lang>.tar`，由 `download_scaffold.sh` 下载）。
- `prd_type`：`fuzzy`，读 `fuzzy_prds*/<alias>/start.md` 并走 Oracle 交互。
- `difficulty`：["normal", "easy", "medium"]，分别对应 `fuzzy_prds/`、`fuzzy_prds_easy/`、`fuzzy_prds_medium/`（PRD 详略程度递增）。
- `user_host`（选填，default="127.0.0.1"）：User Agent 所在主机。
- `user_init_port` / `user_query_port` / `user_eval_port`（选填，默认 50001/50002/50003）：初始化 / 提问 / 交互质量统计端口。参考 `user_agent/example_client.py`。
- `user_model_name`（选填，default="DeepSeek-V3.2"）：Oracle 使用的模型，必须是 `user_model.json` 里的键（DeepSeek-V3.2 / Gemini-3.1-Flash-Lite / Qwen3.5-4B）。初始化阶段同步给 User Agent，由其为 append_id 绑定该模型。
- `append_id`（选填）：一次实验的标识，由 User Agent 返回。带上则 resume，不带则开新实验。
- `query_count`（选填，default=16）：每个 append_id 绑定的最大提问次数。
- `agent_framework`（选填，default="claude-code"）：["claude-code", "openhands"]。

## 生成代码路径

- 代码路径：`results/<append_id>/<alias>`（alias 为匿名编号 `realcode@NNN`）
- 实验注册表：`results/settings.json`（append_id → 实验配置）
- 单次实验设置：`results/<append_id>/settings.json`（配置 + 每仓库结果）

## fuzzy PRD

- Fuzzy PRD Raw：`fuzzy_prds*/<alias>/start.md`（由 `tools/write_fuzzy_prds.py` 从 `user_agent/prd_json*` 生成）。
- Fuzzy Suffix：`user_agent/fuzzy_suffix.md`（追加在 Raw 之后，填入本次运行的 host/query_port/append_id/task_id，告诉被测 Agent 如何向 Oracle 提问）。

完整 PRD = Fuzzy PRD Raw + 填好参数的 Fuzzy Suffix，写到 `fuzzy_prds*@<user_model_name>@query_<query_count>/<alias>/start.md`，每次运行刷新。

## 评测指标

(a) Dynamic Test Execution（容器内跑权威测试，host 端比对 stdout）
- Public Test Cases Pass Rate
- Test Cases Pass Rate（Native / hidden）
- Enhanced Test Cases Pass Rate

(b) Structural Assessment（host 端，对比生成树与 golden 原始源码）
- File Count / LOC
- Class Similarity
- Method Similarity

(c) Agentic Evaluation（Critic Model 打分，三个独立的 0–1 分）
- Semantic Similarity
- API Similarity
- Design Quality

(d) Interaction Quality（由 User Agent 经 user_eval_port 统计）
- Constraint Coverage
- Fallback Rate
- Budget Usage Rate
