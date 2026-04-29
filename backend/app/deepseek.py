from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .models import EvaluationPayload, ReportContent, ScoreBreakdown

load_dotenv()


SYSTEM_PROMPT = """你是 ACL 重建术后康复训练辅助评估助手。
只能基于用户提供的结构化动作指标给出康复训练建议，不得声称做出医学诊断。
请输出 JSON，字段必须为 overallScore, scoreBreakdown, riskTips, nextPlan, reportText。
scoreBreakdown 包含 rangeOfMotion, symmetry, stability, form 四个 0-100 整数。
riskTips 和 nextPlan 分别给 3-5 条中文短句。"""


def build_prompt(payload: EvaluationPayload) -> str:
    action_name = "深蹲" if payload.actionType == "squat" else "走路"
    return json.dumps(
        {
            "任务": f"根据结构化指标生成{action_name}康复辅助评估报告",
            "隐私约束": "没有原始视频、图片帧或摄像头画面，只有浏览器端计算后的结构化数据。",
            "医学限制": "本工具不作为正式医学诊断。",
            "结构化指标": payload.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )


def generate_report(payload: EvaluationPayload) -> ReportContent:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return fallback_report(payload, "未配置 DeepSeek API Key，已使用本地规则生成报告。")

    try:
        llm = ChatOpenAI(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=0.2,
        )
        response = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=build_prompt(payload)),
        ])
        content = response.content if isinstance(response.content, str) else json.dumps(response.content, ensure_ascii=False)
        return parse_report(content, payload)
    except Exception as exc:
        return fallback_report(payload, f"DeepSeek 调用失败，已使用本地规则生成报告：{exc}")


def parse_report(text: str, payload: EvaluationPayload) -> ReportContent:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("DeepSeek response did not contain JSON")
    data = json.loads(match.group(0))
    scores = payload.preliminaryScores
    data.setdefault("overallScore", scores.overall)
    data.setdefault("scoreBreakdown", {
        "rangeOfMotion": scores.rangeOfMotion,
        "symmetry": scores.symmetry,
        "stability": scores.stability,
        "form": scores.form,
    })
    data.setdefault("riskTips", [])
    data.setdefault("nextPlan", [])
    data.setdefault("reportText", text)
    return ReportContent.model_validate(data)


def fallback_report(payload: EvaluationPayload, note: str) -> ReportContent:
    scores = payload.preliminaryScores
    summary = payload.summary
    risks: list[str] = []
    plan: list[str] = []

    if summary.kneeSymmetryDiffAvg > 10:
        risks.append("左右膝关节角度差偏大，训练时应降低速度并关注患侧代偿。")
    if summary.kneeValgusIndexAvg > 0.18:
        risks.append("检测到膝内扣风险，建议强化髋外展和臀中肌控制。")
    if summary.trunkLeanAvg > 25:
        risks.append("躯干前倾较明显，可能增加膝关节和腰背负担。")
    if scores.stability < 70:
        risks.append("动作稳定性不足，建议在保护环境下进行低负荷训练。")
    if not risks:
        risks.append("未发现明显高风险信号，但仍需遵医嘱逐步增加训练量。")

    if payload.actionType == "squat":
        plan.extend([
            "继续进行半蹲到可控深度的闭链训练，优先保持膝盖朝向脚尖。",
            "加入台阶上落、弹力带髋外展等控制训练，每组保持动作慢而稳定。",
            "若出现肿胀、疼痛或不稳感，应停止训练并咨询康复治疗师。",
        ])
    else:
        plan.extend([
            "以短距离、平地、稳定节律步行为主，逐步延长连续步行时间。",
            "训练时关注左右步幅和摆腿幅度，避免为了速度牺牲对称性。",
            "可加入重心转移和单腿支撑练习，提升支撑相稳定性。",
        ])

    report_text = (
        f"{note}\n"
        f"本次结构化评估得到综合康复评分 {scores.overall} 分。"
        f"关节活动度 {scores.rangeOfMotion} 分，左右对称性 {scores.symmetry} 分，"
        f"稳定性 {scores.stability} 分，动作标准度 {scores.form} 分。"
        "这些结果仅用于康复训练辅助观察，不替代医生或康复治疗师的判断。"
    )

    return ReportContent(
        overallScore=scores.overall,
        scoreBreakdown=ScoreBreakdown(
            rangeOfMotion=scores.rangeOfMotion,
            symmetry=scores.symmetry,
            stability=scores.stability,
            form=scores.form,
        ),
        riskTips=risks[:5],
        nextPlan=plan[:5],
        reportText=report_text,
    )
