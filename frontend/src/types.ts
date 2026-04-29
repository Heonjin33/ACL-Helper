export type ActionType = 'walk' | 'squat'
export type DetectionMode = 'upload' | 'camera'

export interface JointAngles {
  leftKnee: number
  rightKnee: number
  leftHip: number
  rightHip: number
  trunkLean: number
}

export interface FrameMetric {
  timestampMs: number
  visibility: number
  angles: JointAngles
  kneeValgusIndex: number
  hipCenterX: number
  hipCenterY: number
  ankleSpread: number
  kneeSpread: number
  leftAnkleX: number
  rightAnkleX: number
}

export interface ScoreBreakdown {
  rangeOfMotion: number
  symmetry: number
  stability: number
  form: number
}

export interface EvaluationPayload {
  actionType: ActionType
  mode: DetectionMode
  durationSec: number
  repetitions: number
  frameCount: number
  summary: {
    kneeFlexionAvg: number
    kneeFlexionMax: number
    hipFlexionAvg: number
    hipFlexionMax: number
    trunkLeanAvg: number
    kneeSymmetryDiffAvg: number
    kneeValgusIndexAvg: number
    stabilityIndex: number
    gaitCycleSymmetry?: number
    kneeRangeOfMotion?: number
    hipRangeOfMotion?: number
    swingAmplitudeDiff?: number
    rhythmStability?: number
  }
  preliminaryScores: ScoreBreakdown & { overall: number }
  privacyNote: string
  generatedAt: string
}

export interface ReportResponse {
  id: number
  overallScore: number
  scoreBreakdown: ScoreBreakdown
  riskTips: string[]
  nextPlan: string[]
  reportText: string
  pdfUrl: string
  createdAt: string
}

export interface HistoryRecord {
  id: string
  payload: EvaluationPayload
  report?: ReportResponse
}
