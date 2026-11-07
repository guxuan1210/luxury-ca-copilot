# CHENGYU 客户顾问 AI Copilot

面向奢侈品牌客户顾问（Client Advisor）的中文微信话术辅助工具。系统根据客户信息、沟通场景、历史对话与产品信息，自动生成 **三条不同策略的中文微信候选话术**，供客户顾问选择。

这是 **Artefact Applied AI Engineer Written Challenge** 的提交项目。所有客户、产品、活动与交易数据均为虚构。

---

## 快速开始

### 1. 环境准备

```bash
python --version   # 需要 3.11+
pip install -r requirements.txt
```

### 2. 配置 API 密钥

复制 `.env.example` 为 `.env`，填入真实值：

```bash
cp .env.example .env
```

```ini
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-pro
ANTHROPIC_AUTH_TOKEN=sk-xxxxxxxxxxxxxxxx
```

`.env` 已被 `.gitignore` 排除，请勿提交密钥。

### 3. 启动交互式 Demo

```bash
streamlit run app.py
```

在浏览器中选择业务场景、填写客户信息与历史对话，点击「生成」即可得到三条候选话术。

### 4. 重建测试集（可选）

```bash
python scripts/build_test_cases.py
```

### 5. 批量生成 Baseline

```bash
python scripts/run_generation.py
```

> **Prompt 版本切换**：默认使用 V2.0（最终版）。要复现 V1.0 基线，用 `CHENGYU_MODEL_VERSION=v1.0` 前缀运行（Windows PowerShell：`$env:CHENGYU_MODEL_VERSION="v1.0"; python scripts/run_generation.py`）。两版产出已分别归档为 `data/*_v1.0.*` 与 `data/*_v2.0.*`。

产出：
- `data/generated_outputs.csv`（官方 8 列格式）
- `data/run_metadata.csv`（版本 / 延迟 / token 追踪）
- `data/generated_outputs.jsonl`（结构化输出，供评估使用）

### 6. 批量评估（规则检查 + LLM-as-Judge）

```bash
python scripts/run_evaluation.py
```

产出：
- `evaluation/results.csv`
- `evaluation/summary.json`
- `evaluation/defect_log.csv`

### 7. 运行单元测试

```bash
python -m pytest tests/ -q
```

---

## 项目结构

```text
luxury-ca-copilot/
├── app.py                        # Streamlit 交互 Demo
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── src/
│   ├── config.py                 # 配置 / 路径 / 模型参数
│   ├── schemas.py                # Pydantic 输入输出模型
│   ├── llm.py                    # LLM 客户端工厂 + 文本提取
│   ├── prompt_builder.py         # System / User Prompt 组装与 JSON 解析
│   ├── generator.py              # 生成 + 校验 + 有界重试
│   └── validator.py              # 规则校验（硬检查 + 软提示）
│
├── prompts/
│   ├── brand_guidelines.md       # 品牌语气与沟通规则
│   ├── system_prompt.md          # System Prompt 模板（V1.0）
│   ├── system_prompt_v2.md       # System Prompt 模板（V2.0）
│   └── scenario_rules.yaml       # 六场景专属规则
│
├── data/
│   ├── products.json             # 虚构产品目录
│   ├── test_cases.jsonl          # 50 个测试案例
│   ├── generated_outputs.csv     # 官方 8 列输出
│   └── run_metadata.csv          # 版本与运行元数据
│
├── evaluation/
│   ├── evaluator.py              # 规则检查 + LLM Judge
│   ├── judge_prompt.md           # 评审 Rubric
│   ├── results.csv               # 逐案例评分
│   ├── summary.json              # 汇总统计
│   └── defect_log.csv            # 缺陷记录
│
├── scripts/
│   ├── build_test_cases.py       # 构建 50 案例
│   ├── run_generation.py         # 批量生成
│   ├── run_evaluation.py         # 批量评估
│   └── make_charts.py            # 评估图表
│
├── reports/
│   ├── work_log.md               # A. 工作日志
│   ├── methodology.md            # B. 方法论
│   ├── evaluation_report.md      # D. 评估报告
│   └── defects_and_next_steps.md # E. 缺陷与下一步
│
└── tests/
    ├── test_schema.py
    ├── test_validator.py
    └── test_generation.py
```

---

## 六个业务场景

| ID | 场景 |
|---|---|
| S1 | 生日与节日问候（birthday_festive） |
| S2 | 产品推荐（product_recommendation） |
| S3 | 售后关怀（post_purchase_care） |
| S4 | 沉睡客户唤醒（reactivation） |
| S5 | 活动邀请（event_invitation） |
| S6 | 价格异议（price_objection） |

## 三条候选话术策略

| 输出 | 策略 | 目标 |
|---|---|---|
| Output 1 | concise_elegant | 简洁、自然，适合日常微信 |
| Output 2 | warm_personalized | 强调客户关系与个性化 |
| Output 3 | contextual_consultative | 结合情境，轻咨询式沟通 |

---

## 评价体系（简要）

- **五项质量指标**（1–5 分）：相关性 25%、个性化 20%、品牌一致性 20%、自然度 20%、上下文一致性 15%。
- **独立门槛**：恰好三条输出、结构化输出有效、无未授权事实声明、无客户边界违规、候选差异度 ≥ 4.0。
- **三层评价**：L1 规则检查（确定性）→ L2 LLM-as-Judge（固定 Rubric）→ L3 人工复核。

详见 `reports/methodology.md` 与 `reports/evaluation_report.md`。

---

## 注意事项

- 本项目仅用于笔试演示，不连接真实 CRM、不自动发送微信。
- 所有数据均为虚构，不包含任何真实个人信息。
- 生成内容供客户顾问参考，实际发送前需人工复核。
