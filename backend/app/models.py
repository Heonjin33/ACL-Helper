from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ActionType = Literal["walk", "squat"]
DetectionMode = Literal["upload", "camera"]


class ScoreBreakdown(BaseModel):
    rangeOfMotion: int = Field(ge=0, le=100)
    symmetry: int = Field(ge=0, le=100)
    stability: int = Field(ge=0, le=100)
    form: int = Field(ge=0, le=100)


class PreliminaryScores(ScoreBreakdown):
    overall: int = Field(ge=0, le=100)


class EvaluationSummary(BaseModel):
    kneeFlexionAvg: float = 0
    kneeFlexionMax: float = 0
    hipFlexionAvg: float = 0
    hipFlexionMax: float = 0
    trunkLeanAvg: float = 0
    kneeSymmetryDiffAvg: float = 0
    kneeValgusIndexAvg: float = 0
    stabilityIndex: float = 0
    gaitCycleSymmetry: float | None = None
    kneeRangeOfMotion: float | None = None
    hipRangeOfMotion: float | None = None
    swingAmplitudeDiff: float | None = None
    rhythmStability: float | None = None


class EvaluationPayload(BaseModel):
    actionType: ActionType
    mode: DetectionMode
    durationSec: float = Field(ge=0)
    repetitions: int = Field(ge=0)
    frameCount: int = Field(ge=0)
    summary: EvaluationSummary
    preliminaryScores: PreliminaryScores
    privacyNote: str
    generatedAt: datetime


class ReportContent(BaseModel):
    overallScore: int = Field(ge=0, le=100)
    scoreBreakdown: ScoreBreakdown
    riskTips: list[str]
    nextPlan: list[str]
    reportText: str


class ReportResponse(ReportContent):
    id: int
    pdfUrl: str
    createdAt: datetime
