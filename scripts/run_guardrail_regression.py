"""V2.1 guardrail regression: prove the send_at (temporal) and do_not_contact (block) guardrails.

Runs 12 targeted cases:
  - 6 do_not_contact: generate() must hard-block (no LLM call) and return an acknowledgment.
  - 6 send_at: generate() must not emit forbidden relative-time terms (今天/明天/...).

Writes:
  - data/regression_cases_v2.1.jsonl   (inputs, for artifact transparency)
  - data/regression_results_v2.1.csv   (pass/fail per case)
  - data/regression_evidence_v2.1.txt  (human-readable outputs / block messages)
"""
from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.generator import generate
from src.schemas import ClientInfo, EventInfo, Message, TestCase

ALL_RELATIVE = list(config.RELATIVE_TIME_TERMS)


def _case(case_id, scenario, guardrail, forbidden, *, notes="", history=None,
          event=None, send_at="", prefs=None):
    return {
        "case_id": case_id,
        "scenario": scenario,
        "guardrail": guardrail,
        "forbidden": forbidden,
        "case": TestCase(
            case_id=case_id,
            scenario=scenario,
            client=ClientInfo(name="测试客户", preferred_tone="elegant",
                              preferences=prefs or [], notes=notes),
            conversation_history=history or [],
            event_information=event,
            send_at=send_at,
        ),
    }


def _evt(date, title="CHENGYU 私人预览", location="上海旗舰店"):
    return EventInfo(title=title, date=date, location=location, format="定向邀约的私人预览", note="")


CASES = [
    # ---- do_not_contact guardrail (must block) ----
    _case("RG-DNC-01", "reactivation", "do_not_contact", [],
          notes="客户明确表示别再联系我，已退订短信。"),
    _case("RG-DNC-02", "reactivation", "do_not_contact", [],
          history=[Message(role="client", content="请勿再联系我，谢谢。")]),
    _case("RG-DNC-03", "product_recommendation", "do_not_contact", [],
          notes="客户要求停止联系。"),
    _case("RG-DNC-04", "event_invitation", "do_not_contact", [],
          history=[Message(role="client", content="别再发了，我不想再收到活动邀请。")]),
    _case("RG-DNC-05", "birthday_festive", "do_not_contact", [],
          notes="不要再联系了。"),
    _case("RG-DNC-06", "post_purchase_care", "do_not_contact", [],
          history=[Message(role="client", content="请帮我退订，不再接收任何消息。")]),

    # ---- send_at guardrail (no forbidden relative-time terms) ----
    # No send_at: model has no "today" anchor, so it must not use relative terms.
    _case("RG-SAT-01", "birthday_festive", "send_at", ALL_RELATIVE,
          notes="生日：11月6日。喜欢木质调。", prefs=["woody", "cedar"]),
    _case("RG-SAT-02", "birthday_festive", "send_at", ALL_RELATIVE,
          notes="生日：11月9日。"),
    _case("RG-SAT-03", "event_invitation", "send_at", ALL_RELATIVE,
          event=_evt("11月18日 19:00")),
    # send_at provided days before the event: "今天/明天/后天" are all wrong.
    _case("RG-SAT-04", "event_invitation", "send_at", ["今天", "明天", "后天"],
          event=_evt("11月18日 19:00"), send_at="2026-11-10 10:00"),
    # send_at = birthday itself: "明天/后天/昨天" wrong, "今天" acceptable.
    _case("RG-SAT-05", "birthday_festive", "send_at", ["明天", "后天", "昨天"],
          notes="生日：11月6日。", send_at="2026-11-06 09:00"),
    # send_at = event day: "明天/后天" wrong.
    _case("RG-SAT-06", "event_invitation", "send_at", ["明天", "后天"],
          event=_evt("11月18日 19:00"), send_at="2026-11-18 18:00"),
]


def _forbidden_hits(forbidden, texts):
    return [t for t in forbidden for txt in texts if t in txt]


def main():
    data_dir = config.DATA_DIR

    # Write inputs for transparency.
    with open(data_dir / "regression_cases_v2.1.jsonl", "w", encoding="utf-8") as f:
        for c in CASES:
            f.write(c["case"].model_dump_json() + "\n")

    rows, evidence = [], []
    n_pass = n_fail = 0
    for c in CASES:
        t0 = time.time()
        result = generate(c["case"])
        elapsed = time.time() - t0

        if c["guardrail"] == "do_not_contact":
            ok = result.blocked and result.block_reason == "do_not_contact" and result.block_message
            detail = f"blocked={result.blocked}, reason={result.block_reason}" if not ok else "硬性拦截，返回停联确认"
            texts = [result.block_message] if result.block_message else []
            evidence.append(f"--- {c['case_id']} ({c['guardrail']}) ---")
            evidence.append("输入：" + (c['case'].client.notes or c['case'].conversation_history[0].content))
            evidence.append("结果：" + ("BLOCKED" if result.blocked else "NOT BLOCKED"))
            evidence.append("确认话术：" + (result.block_message or ""))
        else:
            texts = [m.text for m in result.output.messages] if result.output else []
            hits = _forbidden_hits(c["forbidden"], texts)
            ok = bool(texts) and not hits
            detail = "输出含禁用时间词: " + ", ".join(hits) if hits else ("生成失败: " + result.error if not texts else "通过（无禁用相对时间词）")
            evidence.append(f"--- {c['case_id']} ({c['guardrail']}) ---")
            evidence.append("send_at：" + (c['case'].send_at or "未提供"))
            evidence.append("禁用词：" + ", ".join(c["forbidden"]))
            for i, t in enumerate(texts, 1):
                evidence.append(f"O{i}: {t}")
            evidence.append("命中禁用词：" + (", ".join(hits) if hits else "无"))

        if ok:
            n_pass += 1
        else:
            n_fail += 1
        rows.append({
            "Case ID": c["case_id"],
            "Guardrail": c["guardrail"],
            "Scenario": c["scenario"],
            "Expectation": "blocked" if c["guardrail"] == "do_not_contact"
                           else "no terms: " + ",".join(c["forbidden"]),
            "Result": "PASS" if ok else "FAIL",
            "Detail": detail,
            "Latency s": round(elapsed, 1),
        })
        print(f"[{c['case_id']}] {'PASS' if ok else 'FAIL'} ({elapsed:.1f}s)")

    with open(data_dir / "regression_results_v2.1.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["Case ID", "Guardrail", "Scenario", "Expectation",
                                          "Result", "Detail", "Latency s"])
        w.writeheader()
        w.writerows(rows)

    (data_dir / "regression_evidence_v2.1.txt").write_text("\n\n".join(evidence), encoding="utf-8")

    print(f"\nRegression: {n_pass} passed, {n_fail} failed (of {len(CASES)})")
    print(f"Wrote {data_dir / 'regression_cases_v2.1.jsonl'}")
    print(f"Wrote {data_dir / 'regression_results_v2.1.csv'}")
    print(f"Wrote {data_dir / 'regression_evidence_v2.1.txt'}")


if __name__ == "__main__":
    main()
