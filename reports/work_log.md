# A. Work Log（工作日志）

> 本日志按 Brief 建议的 13 个步骤记录核心开发工作，另以 Step 14 记录提交前的 V2.1 护栏迭代。Screenshots 列：开发阶段（S01–S08、S10–S12）会话目录已删除，以代码/测试佐证；S09 与 S13 见 `reports/screenshots/`。

## A.1 Development Timeline（开发时间线）

| 日期 | 阶段 | 产出 |
|---|---|---|
| 2026-11-03 | 品牌设定 + 核心开发 | 品牌规则、Schema、Prompt V1、生成器、校验器、Demo、单元测试 |
| 2026-11-04 | 测试集 + 评估模块 | 50 案例、生成/评估脚本、LLM-as-Judge 评估器 |
| 2026-11-05 | Baseline 生成 + 评估 + 迭代 + 报告 | V1.0 生成与评估、缺陷分析、V2.0 迭代、五份报告 |
| 2026-11-07 | 交叉复核 + V2.1 护栏 + 提交准备 | ChatGPT 交叉检验、send_at + do_not_contact 护栏、缺陷表闭环、回归验证、README、密钥清理 |

## A.2 Tools and AI Assistance（工具与 AI 辅助）

| 工具 / 智能体 | 用途 |
|---|---|
| Claude Code（AI 编程助手） | 需求拆解、代码实现、测试案例设计、报告撰写 |
| ChatGPT（模型 6.1，交叉评审） | 读取项目、交叉检验、提出 V2.1 护栏修改建议 |
| Python 3.11 | 核心逻辑、批量脚本、评估脚本 |
| Pydantic | 输入/输出 Schema 校验 |
| Streamlit | 交互式 Demo |
| LLM API（deepseek-v4-pro，Anthropic 兼容端点） | 话术生成 + LLM-as-Judge 评审 |

## A.3 Step-by-step Log（逐步记录）

| Step | What you did | Input | Output | Tool or agent used | Screenshots |
|---|---|---|---|---|---|
| 1 | 需求分析：将 Written Brief 转化为需求清单，明确 6 场景与交付范围 | Written Brief | 需求清单（见 B.1） | AI / Manual | 无（会话已删除，见代码/测试） |
| 2 | 品牌设计：虚构 CHENGYU 品牌、语气六维度、Allowed/Prohibited 规则 | 品牌假设 | brand_guidelines.md | AI | 无（会话已删除，见代码/测试） |
| 3 | 系统架构：单管线设计 + Mermaid 图 | 需求 | 架构图（见 B.3） | Diagram / AI | 无（会话已删除，见代码/测试） |
| 4 | Prompt 开发：System Prompt + scenario_rules.yaml（V1.0，后迭代至 V2.0） | 品牌 + 场景 | Prompt V1.0 / V2.0 | AI / Python | 无（会话已删除，见代码/测试） |
| 5 | 原型开发：schemas / prompt_builder / generator / validator / app.py | 输入 Schema | 可运行工具 | Python / Streamlit | 无（会话已删除，见代码/测试） |
| 6 | 测试设计：build_test_cases.py 构建 50 案例 | 场景覆盖矩阵 | test_cases.jsonl | AI / Python | 无（会话已删除，见代码/测试） |
| 7 | Baseline 测试：run_generation.py 批量生成 | 50 案例 | generated_outputs.csv（150 条输出） | Python / LLM | 无（会话已删除，见代码/测试） |
| 8 | 评估：run_evaluation.py（规则检查 + LLM Judge） | V1 输出 | results.csv / summary.json | Python / LLM Judge | 无（会话已删除，见代码/测试） |
| 9 | 缺陷分析：从规则 flag 与 Judge 标记汇总缺陷 | 评估结果 | defect_log.csv | AI / Manual | 见 reports/screenshots/S09_defect_review.jpg |
| 10 | 迭代：根据缺陷更新 Prompt（新增硬性规则 10/11 与候选差异度要求） | 缺陷 + V1 Prompt | Prompt V2.0 | Python / AI | 无（会话已删除，见代码/测试） |
| 11 | 回归测试：固定 12 案例（每场景 2 个）V1.0 与 V2.0 前后对比 | 固定输入 | 前后对比 | Python / LLM | 无（会话已删除，见代码/测试） |
| 12 | 最终验证：用未见过的新输入验证工具 | 新虚构案例 | 三条候选话术 | Streamlit | 无（会话已删除，见代码/测试） |
| 13 | 提交准备：清理密钥、整理附件、README | 全部产出 | 最终包 | Manual | 见 reports/screenshots/S13_submission.jpg |
| 14 | 交叉复核与 V2.1 护栏：ChatGPT 读取项目并交叉检验，提出 send_at 时间护栏与 do_not_contact 停止联系拦截建议；补缺陷表闭环、实现两条护栏、12 个回归案例验证 | 项目代码 + ChatGPT 交叉评审 | V2.1 护栏 + 回归结果 | ChatGPT（模型 6.1）+ Claude Code + Python | 无（以代码 + data/regression_results_v2.1.csv 佐证） |

## A.4 关键实现记录

- **发现并解决：思考型模型 token 耗尽问题。** 评审任务中 `deepseek-v4-pro` 的思考过程会耗尽 `max_tokens=3000`，导致最终答案为空（`stop_reason=max_tokens`）。根因是思考型模型在输出最终文本前先产生大量 reasoning token。修复：将基础预算提升到 8000，并在截断时按 `[8000, 12000, 16000]` 自动升级重试（`src/generator.py`、`evaluation/evaluator.py`）。
- **发现并解决：Windows 控制台编码乱码。** 终端显示中文乱码仅为控制台 GBK 显示问题；所有文件写入均显式使用 `encoding="utf-8"`（CSV 使用 `utf-8-sig` 以便 Excel 正确识别），实际内容正确。
- **事实约束的工程化。** 通过「仅可使用以下事实」的输入块标注 + 折扣/优惠关键词软提示 + LLM Judge 事实错误标记 + 人工复核，三层机制约束编造。
- **Prompt 版本化与回归。** 通过 `CHENGYU_MODEL_VERSION` 环境变量切换 `prompts/system_prompt.md`（V1.0）与 `prompts/system_prompt_v2.md`（V2.0），脚本无需改动即可对比两版。V2.0 新增：硬性规则 10（不得对定价原因/留香时长/香精浓度做未经证实的因果推断）、规则 11（客户明确要求减少联系时进一步克制为非营销问候），以及「三条候选差异度」显式要求（不同开头、长短句节奏、侧重点）。
- **评审缓存与单次调用修复。** `run_evaluation.py` 以 `case_id|version|输出摘要哈希` 为键缓存 Judge 结果，避免重复计费；并修复了「缓存未命中时 Judge 被重复调用、且误标 `judge output not parseable`」的缺陷（见脚本内注释）。
- **V2.1 护栏加固（11-07，由 ChatGPT 交叉评审驱动）。** ChatGPT（模型 6.1，会话 https://chatgpt.com/share/6aef2949-db48-83e8-b9d8-9077969750ee）读取项目并做交叉检验后，提出两条 V2.1 修改建议：① send_at 时间护栏——未提供发送时间时禁用「今天/明天」等相对时间词；② do_not_contact 停止联系护栏——客户明确停联时不调用 LLM、直接返回单条停联确认。据此实现两条护栏、补齐 V2.0 缺陷表闭环，并以 12 个专项回归案例验证（12/12 通过，见 E.8 与 `data/regression_results_v2.1.csv`）。

## A.5 说明

- 实际开发在 2026-11-03 至 11-05 的三个工作会话内完成，11-07 做交叉复核、V2.1 护栏迭代与提交准备；文件修改时间与归档数据（`run_id`、`*_v1.0.*` / `*_v2.0.*` / `regression_*_v2.1.*`）可佐证该时间线。
- 开发阶段所用 coding agent 的会话目录已在交付前删除，故 S01–S08 与 S10–S12 无法提供原始聊天截图，相应步骤以代码、测试结果与文件时间戳佐证；S09（缺陷复核）与 S13（提交准备）来自 11-07 的真实复核会话，截图见 `reports/screenshots/`。
