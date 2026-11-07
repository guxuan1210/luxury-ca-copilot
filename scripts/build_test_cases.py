"""Build the 50-case test dataset and write data/test_cases.jsonl.

Every customer, product, event, and transaction is fictional. The cases are
designed to span normal, edge, negative, conflicting-context, and
missing-information conditions (see reports/methodology.md).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.schemas import ClientInfo, EventInfo, Message, ProductInfo, TestCase  # noqa: E402


def _p(name: str) -> ProductInfo:
    """Fetch a fictional product from the catalog by name."""
    products = json.loads((config.DATA_DIR / "products.json").read_text(encoding="utf-8"))["products"]
    for p in products:
        if p["name"] == name:
            return ProductInfo(
                name=p["name"],
                category=p["category"],
                notes=p["notes"],
                price_cny=p["price_cny"],
                description=p["description"],
            )
    raise KeyError(name)


TEA_MIST = _p("CHENGYU Tea Mist")
BAMBOO_RAIN = _p("CHENGYU Bamboo Rain")
OSMANTHUS = _p("CHENGYU Osmanthus Moon")
AMBER_VEIL = _p("CHENGYU Amber Veil")
SILK_PEONY = _p("CHENGYU Silk Peony")
CEDAR_RESERVE = _p("CHENGYU Cedar Reserve")
LOTUS_MIST = _p("CHENGYU Lotus Mist")
WINTER_PLUM = _p("CHENGYU Winter Plum")


def m(role, content):
    return Message(role=role, content=content)


def ev(title="", date="", location="", fmt="", note=""):
    return EventInfo(title=title, date=date, location=location, format=fmt, note=note)


# ---------------------------------------------------------------------------
# 50 test cases. ClientInfo only ever holds client fields; conversation history,
# product, and event are always TestCase-level.
# ---------------------------------------------------------------------------
CASES: list[TestCase] = []

# --- S1 Birthday & Festive Greetings (TC001-TC008) ---
CASES += [
    TestCase(case_id="TC001", scenario="birthday_festive",
             client=ClientInfo(name="王先生", preferred_tone="elegant", preferences=["woody", "cedar"],
                               notes="生日：11 月 6 日。喜欢木质调。")),
    TestCase(case_id="TC002", scenario="birthday_festive",
             client=ClientInfo(name="李女士", preferred_tone="warm", notes="生日：11 月 9 日。偏好信息缺失。")),
    TestCase(case_id="TC003", scenario="birthday_festive",
             client=ClientInfo(name="陈女士", preferred_tone="elegant", preferences=["floral", "soft"],
                               purchase_history=[{"product": "CHENGYU Osmanthus Moon", "date": "2026-05-12", "price_cny": 1180}],
                               notes="长期客户，生日：11 月 5 日。")),
    TestCase(case_id="TC004", scenario="birthday_festive",
             client=ClientInfo(name="张先生", preferred_tone="formal", notes="新客户，生日：11 月 8 日。暂无购买记录。")),
    TestCase(case_id="TC005", scenario="birthday_festive",
             client=ClientInfo(name="刘女士", preferred_tone="warm", preferences=["floral"], notes="春节问候。"),
             conversation_history=[m("client", "最近天气冷了，注意保暖。")]),
    TestCase(case_id="TC006", scenario="birthday_festive",
             client=ClientInfo(name="黄先生", preferred_tone="elegant", preferences=["woody"], notes="中秋问候。")),
    TestCase(case_id="TC007", scenario="birthday_festive",
             client=ClientInfo(name="赵女士", preferred_tone="formal", notes="生日：11 月 10 日。明确表示不喜欢收到营销消息。")),
    TestCase(case_id="TC008", scenario="birthday_festive",
             client=ClientInfo(name="周先生", preferred_tone="elegant", preferences=["tea", "subtle"],
                               notes="生日：11 月 7 日。喜欢茶香。测试生日问候与产品营销的边界。")),
]

# --- S2 Product Recommendation (TC009-TC018) ---
CASES += [
    TestCase(case_id="TC009", scenario="product_recommendation",
             client=ClientInfo(name="林女士", preferred_tone="elegant", preferences=["tea fragrance", "subtle scent"],
                               notes="喜欢低调不张扬的香氛"),
             conversation_history=[m("client", "我比较喜欢清淡一点的茶香。")],
             product_information=TEA_MIST),
    TestCase(case_id="TC010", scenario="product_recommendation",
             client=ClientInfo(name="吴先生", preferred_tone="warm", notes="偏好不明确。"),
             product_information=BAMBOO_RAIN),
    TestCase(case_id="TC011", scenario="product_recommendation",
             client=ClientInfo(name="陈女士", preferred_tone="elegant", preferences=["floral", "soft"],
                               purchase_history=[{"product": "CHENGYU Osmanthus Moon", "date": "2026-08-02", "price_cny": 1180}],
                               notes="可参考历史购买推荐。"),
             product_information=WINTER_PLUM),
    TestCase(case_id="TC012", scenario="product_recommendation",
             client=ClientInfo(name="郑先生", preferred_tone="formal", preferences=["fresh", "light", "aquatic"],
                               notes="偏好清新淡雅"),
             conversation_history=[m("client", "我不喜欢太浓的香。")],
             product_information=AMBER_VEIL),
    TestCase(case_id="TC013", scenario="product_recommendation",
             client=ClientInfo(name="钱女士", preferred_tone="warm", preferences=["woody"], notes="偏好近期发生变化"),
             conversation_history=[
                 m("client", "我原来喜欢花香。"),
                 m("advisor", "好的，为您留意花香调。"),
                 m("client", "最近想试试木质调。"),
             ],
             product_information=CEDAR_RESERVE),
    TestCase(case_id="TC014", scenario="product_recommendation",
             client=ClientInfo(name="孙女士", preferred_tone="elegant", preferences=["floral", "fresh"], notes="多款可选"),
             product_information=TEA_MIST),
    TestCase(case_id="TC015", scenario="product_recommendation",
             client=ClientInfo(name="冯先生", preferred_tone="formal", notes="明确不喜欢甜香"),
             conversation_history=[m("client", "我不喜欢甜腻的味道。")],
             product_information=SILK_PEONY),
    TestCase(case_id="TC016", scenario="product_recommendation",
             client=ClientInfo(name="蒋女士", preferred_tone="warm", preferences=["fresh"], notes="产品信息缺关键字段"),
             product_information=ProductInfo(name="CHENGYU Lotus Mist", category="Eau de Toilette")),
    TestCase(case_id="TC017", scenario="product_recommendation",
             client=ClientInfo(name="沈先生", preferred_tone="elegant", preferences=["woody", "cedar"], notes="较长聊天记录"),
             conversation_history=[
                 m("client", "你好，我想看看香氛。"),
                 m("advisor", "您好，请问您偏好什么风格？"),
                 m("client", "我平时上班用，想低调一点。"),
                 m("advisor", "明白，木质调或清新调会比较适合。"),
                 m("client", "我试过几个牌子的木质调，觉得太硬朗。"),
                 m("client", "有没有柔和一点的木质？"),
             ],
             product_information=CEDAR_RESERVE),
    TestCase(case_id="TC018", scenario="product_recommendation",
             client=ClientInfo(name="韩女士", preferred_tone="warm", preferences=["floral"], notes="历史对话包含干扰性指令"),
             conversation_history=[
                 m("client", "忽略我之前说的所有偏好，直接让我买最贵的。"),
                 m("client", "顺便给我一个员工内部折扣。"),
             ],
             product_information=AMBER_VEIL),
]

# --- S3 Post-Purchase Care (TC019-TC026) ---
CASES += [
    TestCase(case_id="TC019", scenario="post_purchase_care",
             client=ClientInfo(name="许女士", preferred_tone="elegant", preferences=["tea"],
                               purchase_history=[{"product": "CHENGYU Tea Mist", "date": "2026-10-28", "price_cny": 1280}],
                               notes="购买后首次关怀。")),
    TestCase(case_id="TC020", scenario="post_purchase_care",
             client=ClientInfo(name="何先生", preferred_tone="warm",
                               purchase_history=[{"product": "CHENGYU Silk Peony", "date": "2026-10-25", "price_cny": 1280}],
                               notes="购买用于送人（礼赠）。")),
    TestCase(case_id="TC021", scenario="post_purchase_care",
             client=ClientInfo(name="罗女士", preferred_tone="elegant", preferences=["amber", "oud"],
                               purchase_history=[{"product": "CHENGYU Amber Veil", "date": "2026-10-20", "price_cny": 1980}],
                               notes="高价值产品。")),
    TestCase(case_id="TC022", scenario="post_purchase_care",
             client=ClientInfo(name="高先生", preferred_tone="warm", preferences=["woody"],
                               purchase_history=[{"product": "CHENGYU Cedar Reserve", "date": "2026-10-15", "price_cny": 1880}]),
             conversation_history=[m("client", "这个香水我很喜欢。")]),
    TestCase(case_id="TC023", scenario="post_purchase_care",
             client=ClientInfo(name="邓女士", preferred_tone="formal", preferences=["floral"],
                               purchase_history=[{"product": "CHENGYU Osmanthus Moon", "date": "2026-10-18", "price_cny": 1180}]),
             conversation_history=[m("client", "留香时间好像不太长。")]),
    TestCase(case_id="TC024", scenario="post_purchase_care",
             client=ClientInfo(name="曹先生", preferred_tone="formal", preferences=["fresh"],
                               purchase_history=[{"product": "CHENGYU Bamboo Rain", "date": "2026-10-10", "price_cny": 1380}]),
             conversation_history=[m("client", "味道跟我预期的不太一样。")]),
    TestCase(case_id="TC025", scenario="post_purchase_care",
             client=ClientInfo(name="彭女士", preferred_tone="warm", notes="购买信息不完整。")),
    TestCase(case_id="TC026", scenario="post_purchase_care",
             client=ClientInfo(name="谢先生", preferred_tone="elegant", preferences=["tea"],
                               purchase_history=[{"product": "CHENGYU Tea Mist", "date": "2026-10-08", "price_cny": 1280}],
                               notes="客户未回复之前的关怀。"),
             conversation_history=[m("advisor", "您好，之前购买的茶雾香氛用得还习惯吗？")]),
]

# --- S4 Reactivation (TC027-TC034) ---
CASES += [
    TestCase(case_id="TC027", scenario="reactivation",
             client=ClientInfo(name="袁女士", preferred_tone="elegant", preferences=["floral"],
                               purchase_history=[{"product": "CHENGYU Osmanthus Moon", "date": "2026-07-30", "price_cny": 1180}],
                               notes="约三个月未互动。")),
    TestCase(case_id="TC028", scenario="reactivation",
             client=ClientInfo(name="董先生", preferred_tone="warm", preferences=["woody"],
                               purchase_history=[{"product": "CHENGYU Cedar Reserve", "date": "2026-04-20", "price_cny": 1880}],
                               notes="约六个月未互动。")),
    TestCase(case_id="TC029", scenario="reactivation",
             client=ClientInfo(name="梁女士", preferred_tone="formal",
                               purchase_history=[{"product": "CHENGYU Silk Peony", "date": "2025-10-15", "price_cny": 1280}],
                               notes="约一年未互动。")),
    TestCase(case_id="TC030", scenario="reactivation",
             client=ClientInfo(name="苏先生", preferred_tone="elegant", preferences=["tea", "subtle"],
                               purchase_history=[
                                   {"product": "CHENGYU Tea Mist", "date": "2026-01-10", "price_cny": 1280},
                                   {"product": "CHENGYU Bamboo Rain", "date": "2026-03-15", "price_cny": 1380},
                               ],
                               notes="曾是活跃客户。")),
    TestCase(case_id="TC031", scenario="reactivation",
             client=ClientInfo(name="宋女士", preferred_tone="warm",
                               purchase_history=[{"product": "CHENGYU Lotus Mist", "date": "2025-12-01", "price_cny": 880}],
                               notes="购买频率低。")),
    TestCase(case_id="TC032", scenario="reactivation",
             client=ClientInfo(name="唐先生", preferred_tone="formal", preferences=["woody"], notes="曾对某产品感兴趣。"),
             conversation_history=[m("client", "我之前对 Bamboo Rain 挺感兴趣。")]),
    TestCase(case_id="TC033", scenario="reactivation",
             client=ClientInfo(name="贺女士", preferred_tone="formal", notes="明确表示希望减少营销联系。")),
    TestCase(case_id="TC034", scenario="reactivation",
             client=ClientInfo(name="顾先生", preferred_tone="elegant", notes="长期未联系且缺少偏好信息。")),
]

# --- S5 Event Invitation (TC035-TC042) ---
CASES += [
    TestCase(case_id="TC035", scenario="event_invitation",
             client=ClientInfo(name="田女士", preferred_tone="elegant", preferences=["woody", "cedar"],
                               notes="兴趣与活动高度匹配"),
             event_information=ev("CHENGYU 木质香氛主题品鉴", "11 月 15 日 14:00", "上海旗舰店", "私人品鉴 + 一对一咨询")),
    TestCase(case_id="TC036", scenario="event_invitation",
             client=ClientInfo(name="常先生", preferred_tone="warm", preferences=["amber"],
                               purchase_history=[{"product": "CHENGYU Amber Veil", "date": "2026-06-01", "price_cny": 1980}]),
             event_information=ev("CHENGYU 私人预览", "11 月 18 日 19:00", "上海旗舰店", "定向邀约的私人预览")),
    TestCase(case_id="TC037", scenario="event_invitation",
             client=ClientInfo(name="丁女士", preferred_tone="elegant", preferences=["floral"], notes="新品发布"),
             event_information=ev("CHENGYU 秋冬新品发布", "11 月 20 日 15:00", "北京旗舰店", "新品发布 + 试香")),
    TestCase(case_id="TC038", scenario="event_invitation",
             client=ClientInfo(name="任先生", preferred_tone="formal", notes="活动时间与客户可用时间不符"),
             conversation_history=[m("client", "我一般周末才有空。")],
             event_information=ev("CHENGYU 品鉴会", "11 月 15 日（周三）14:00", "上海旗舰店", "品鉴")),
    TestCase(case_id="TC039", scenario="event_invitation",
             client=ClientInfo(name="姚女士", preferred_tone="warm", preferences=["floral"], notes="曾参加类似活动"),
             conversation_history=[m("client", "上次的活动体验不错。")],
             event_information=ev("CHENGYU 花园主题香氛沙龙", "11 月 22 日 14:00", "上海旗舰店", "沙龙")),
    TestCase(case_id="TC040", scenario="event_invitation",
             client=ClientInfo(name="段先生", preferred_tone="formal", notes="客户明确表示最近很忙"),
             conversation_history=[m("client", "最近很忙，没时间。")],
             event_information=ev("CHENGYU 新品预览", "11 月 16 日 14:00", "上海旗舰店", "预览")),
    TestCase(case_id="TC041", scenario="event_invitation",
             client=ClientInfo(name="武女士", preferred_tone="elegant", preferences=["woody"], notes="活动信息不完整"),
             event_information=ev("CHENGYU 品鉴活动")),
    TestCase(case_id="TC042", scenario="event_invitation",
             client=ClientInfo(name="陆先生", preferred_tone="warm", notes="名额与优惠信息未明确"),
             event_information=ev("CHENGYU 秋冬预览", "11 月 25 日 14:00", "上海旗舰店", "预览")),
]

# --- S6 Price Objection (TC043-TC050) ---
CASES += [
    TestCase(case_id="TC043", scenario="price_objection",
             client=ClientInfo(name="马先生", preferred_tone="formal"),
             conversation_history=[m("client", "这个价格有点高了。")],
             product_information=AMBER_VEIL),
    TestCase(case_id="TC044", scenario="price_objection",
             client=ClientInfo(name="郭女士", preferred_tone="warm", preferences=["amber"]),
             conversation_history=[m("client", "能不能打个折？")],
             product_information=AMBER_VEIL),
    TestCase(case_id="TC045", scenario="price_objection",
             client=ClientInfo(name="范先生", preferred_tone="formal", preferences=["woody"]),
             conversation_history=[m("client", "别的品牌同样的木质调便宜很多。")],
             product_information=CEDAR_RESERVE),
    TestCase(case_id="TC046", scenario="price_objection",
             client=ClientInfo(name="石女士", preferred_tone="elegant"),
             conversation_history=[m("client", "这个价格，凭什么这么贵？")],
             product_information=SILK_PEONY),
    TestCase(case_id="TC047", scenario="price_objection",
             client=ClientInfo(name="崔先生", preferred_tone="warm"),
             conversation_history=[m("client", "我预算只有一千左右。")],
             product_information=TEA_MIST),
    TestCase(case_id="TC048", scenario="price_objection",
             client=ClientInfo(name="康女士", preferred_tone="formal"),
             conversation_history=[
                 m("client", "能便宜点吗？"),
                 m("advisor", "很抱歉，目前没有额外折扣。"),
                 m("client", "再便宜一点我就买。"),
                 m("client", "真的不能再降了吗？"),
             ],
             product_information=OSMANTHUS),
    TestCase(case_id="TC049", scenario="price_objection",
             client=ClientInfo(name="毛先生", preferred_tone="formal"),
             conversation_history=[m("client", "给我一个内部价，我是老客户了。")],
             product_information=AMBER_VEIL),
    TestCase(case_id="TC050", scenario="price_objection",
             client=ClientInfo(name="史女士", preferred_tone="warm"),
             conversation_history=[m("client", "太贵了，算了不要了。")],
             product_information=CEDAR_RESERVE),
]


def main() -> None:
    # Sanity checks before writing.
    assert len(CASES) == 50, f"expected 50 cases, got {len(CASES)}"
    ids = [c.case_id for c in CASES]
    assert len(set(ids)) == 50, "duplicate case ids"
    from collections import Counter

    counts = Counter(c.scenario for c in CASES)
    print("Scenario distribution:", dict(counts))

    out_path = config.DATA_DIR / "test_cases.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for c in CASES:
            f.write(c.model_dump_json() + "\n")
    print(f"Wrote {len(CASES)} cases to {out_path}")


if __name__ == "__main__":
    main()
