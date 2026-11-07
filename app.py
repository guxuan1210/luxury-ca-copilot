"""CHENGYU Luxury Client Advisor AI Copilot — Streamlit interactive demo."""
from __future__ import annotations

import json

import streamlit as st

from src import config
from src.generator import generate
from src.schemas import ClientInfo, EventInfo, Message, ProductInfo, TestCase
from src.validator import validate_output

st.set_page_config(page_title="CHENGYU 客户顾问 AI Copilot", layout="wide")

SCENARIO_LABELS = {
    "birthday_festive": "生日与节日问候",
    "product_recommendation": "产品推荐",
    "post_purchase_care": "售后关怀",
    "reactivation": "沉睡客户唤醒",
    "event_invitation": "活动邀请",
    "price_objection": "价格异议",
}

STRATEGY_LABELS = {
    "concise_elegant": "简洁优雅",
    "warm_personalized": "温暖个性化",
    "contextual_consultative": "情境咨询",
}


@st.cache_data
def load_products() -> list[dict]:
    path = config.DATA_DIR / "products.json"
    return json.loads(path.read_text(encoding="utf-8"))["products"]


def parse_history(text: str) -> list[Message]:
    messages: list[Message] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("顾问:"):
            messages.append(Message(role="advisor", content=line[3:].strip()))
        elif line.startswith("客户:"):
            messages.append(Message(role="client", content=line[3:].strip()))
        else:
            messages.append(Message(role="client", content=line))
    return messages


st.title("CHENGYU（澄屿）客户顾问 AI Copilot")
st.caption(
    f"Model: {config.ANTHROPIC_MODEL} · Prompt Version: {config.MODEL_VERSION} · "
    "为奢侈品客户顾问生成三条中文微信候选话术"
)

with st.sidebar:
    st.header("输入配置")
    scenario = st.selectbox(
        "业务场景",
        options=list(SCENARIO_LABELS.keys()),
        format_func=lambda s: SCENARIO_LABELS[s],
    )

    st.subheader("客户信息")
    client_name = st.text_input("客户姓名", value="林女士")
    client_tone = st.selectbox("偏好语气", ["elegant", "warm", "formal", "casual"], index=0)
    preferences_raw = st.text_input("客户偏好（逗号分隔）", value="清淡茶香, 克制香调")
    client_notes = st.text_area("备注（可选）", value="喜欢低调、不张扬的香氛")

    st.subheader("历史对话（每行一条，可加前缀 客户:/顾问:）")
    history_raw = st.text_area(
        "对话历史",
        value="客户: 我比较喜欢清淡一点的茶香。\n顾问: 好的，我记下了，之后为您留意。",
        height=120,
    )

    st.subheader("产品信息")
    products = load_products()
    product_names = ["（无产品信息）"] + [p["name"] for p in products]
    product_choice = st.selectbox("选择产品", product_names)
    product = None
    if product_choice != "（无产品信息）":
        p = next(x for x in products if x["name"] == product_choice)
        product = ProductInfo(
            name=p["name"],
            category=p["category"],
            notes=p["notes"],
            price_cny=p["price_cny"],
            description=p["description"],
        )

    event = None
    if scenario == "event_invitation":
        st.subheader("活动信息（仅用于活动邀请场景）")
        event_title = st.text_input("活动主题", value="CHENGYU 秋冬新品私人预览")
        event_date = st.text_input("活动时间", value="11 月 15 日 14:00")
        event_location = st.text_input("活动地点", value="上海旗舰店")
        event_format = st.text_input("活动形式", value="私人预览 + 一对一香氛咨询")
        event_note = st.text_input("说明（可选）", value="")
        event = EventInfo(
            title=event_title,
            date=event_date,
            location=event_location,
            format=event_format,
            note=event_note,
        )

    generate_btn = st.button("生成三条候选话术", type="primary")

col_input, col_output = st.columns([1, 2])

with col_input:
    st.subheader("当前输入摘要")
    preferences = [p.strip() for p in preferences_raw.split(",") if p.strip()]
    history = parse_history(history_raw)
    case = TestCase(
        case_id="INTERACTIVE",
        scenario=scenario,
        client=ClientInfo(
            name=client_name,
            preferred_tone=client_tone,
            preferences=preferences,
            notes=client_notes,
        ),
        conversation_history=history,
        product_information=product,
        event_information=event,
    )
    st.json(case.model_dump())

with col_output:
    st.subheader("生成结果")
    if generate_btn:
        with st.spinner("正在生成…"):
            result = generate(case)
        if not result.success:
            st.error(f"生成失败：{result.error}")
        else:
            vr = validate_output(result.output)
            if not vr.valid:
                st.warning("结构校验未通过：" + "; ".join(vr.errors))
            if vr.flags:
                st.info("需人工复核的提示：" + "; ".join(vr.flags))

            for i, m in enumerate(result.output.messages, start=1):
                with st.container(border=True):
                    st.markdown(f"**输出 {i} · {STRATEGY_LABELS.get(m.strategy, m.strategy)}**")
                    st.write(m.text)

            with st.expander("运行元数据"):
                st.write(
                    {
                        "latency_ms": result.latency_ms,
                        "retries": result.retries,
                        "token_usage": result.token_usage,
                        "model_version": config.MODEL_VERSION,
                    }
                )
