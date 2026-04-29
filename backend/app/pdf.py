from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import EvaluationPayload, ReportContent

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def pdf_dir() -> Path:
    path = Path(__file__).resolve().parents[1] / "data" / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_pdf(report_id: int, payload: EvaluationPayload, report: ReportContent) -> Path:
    path = pdf_dir() / f"acl-helper-report-{report_id}.pdf"
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "ChineseBase",
        parent=styles["BodyText"],
        fontName="STSong-Light",
        fontSize=11,
        leading=18,
        textColor=colors.HexColor("#17364c"),
    )
    title = ParagraphStyle(
        "ChineseTitle",
        parent=base,
        fontSize=20,
        leading=28,
        spaceAfter=12,
    )
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    story = [
        Paragraph("ACL-helper 康复动作辅助评估报告", title),
        Paragraph("免责声明：本报告仅用于康复训练辅助评估，不作为正式医学诊断或治疗决策依据。", base),
        Spacer(1, 12),
    ]

    action = "深蹲" if payload.actionType == "squat" else "走路"
    mode = "摄像头实时检测" if payload.mode == "camera" else "上传视频检测"
    rows = [
        ["动作类型", action, "检测方式", mode],
        ["综合评分", str(report.overallScore), "完成次数/周期", str(payload.repetitions)],
        ["关节活动度", str(report.scoreBreakdown.rangeOfMotion), "左右对称性", str(report.scoreBreakdown.symmetry)],
        ["稳定性", str(report.scoreBreakdown.stability), "动作标准度", str(report.scoreBreakdown.form)],
    ]
    table = Table(rows, colWidths=[82, 130, 92, 130])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f6f2")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cddfdc")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#17364c")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEADING", (0, 0), (-1, -1), 16),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([table, Spacer(1, 14), Paragraph(report.reportText.replace("\n", "<br/>"), base)])

    story.append(Spacer(1, 12))
    story.append(Paragraph("风险提示", base))
    for item in report.riskTips:
        story.append(Paragraph(f"• {item}", base))

    story.append(Spacer(1, 12))
    story.append(Paragraph("下一阶段康复建议", base))
    for item in report.nextPlan:
        story.append(Paragraph(f"• {item}", base))

    doc.build(story)
    return path
