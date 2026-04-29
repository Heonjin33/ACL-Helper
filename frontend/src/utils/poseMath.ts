import type { NormalizedLandmark } from '@mediapipe/tasks-vision'
import type { ActionType, DetectionMode, EvaluationPayload, FrameMetric, JointAngles } from '../types'

const L = {
  leftShoulder: 11,
  rightShoulder: 12,
  leftHip: 23,
  rightHip: 24,
  leftKnee: 25,
  rightKnee: 26,
  leftAnkle: 27,
  rightAnkle: 28,
}

const clamp = (value: number, min = 0, max = 100) => Math.max(min, Math.min(max, value))
const round = (value: number, digits = 1) => Number.isFinite(value) ? Number(value.toFixed(digits)) : 0

function angle(a: NormalizedLandmark, b: NormalizedLandmark, c: NormalizedLandmark) {
  const ab = { x: a.x - b.x, y: a.y - b.y }
  const cb = { x: c.x - b.x, y: c.y - b.y }
  const dot = ab.x * cb.x + ab.y * cb.y
  const mag = Math.hypot(ab.x, ab.y) * Math.hypot(cb.x, cb.y)
  if (!mag) return 0
  return Math.acos(clamp(dot / mag, -1, 1)) * 180 / Math.PI
}

function trunkLean(leftShoulder: NormalizedLandmark, rightShoulder: NormalizedLandmark, leftHip: NormalizedLandmark, rightHip: NormalizedLandmark) {
  const shoulder = midpoint(leftShoulder, rightShoulder)
  const hip = midpoint(leftHip, rightHip)
  const dx = shoulder.x - hip.x
  const dy = shoulder.y - hip.y
  return Math.abs(Math.atan2(dx, -dy) * 180 / Math.PI)
}

function midpoint(a: NormalizedLandmark, b: NormalizedLandmark) {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}

function avg(values: number[]) {
  const valid = values.filter(Number.isFinite)
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : 0
}

function min(values: number[]) {
  const valid = values.filter(Number.isFinite)
  return valid.length ? Math.min(...valid) : 0
}

function max(values: number[]) {
  const valid = values.filter(Number.isFinite)
  return valid.length ? Math.max(...valid) : 0
}

function std(values: number[]) {
  const mean = avg(values)
  return Math.sqrt(avg(values.map((value) => (value - mean) ** 2)))
}

function countSquats(frames: FrameMetric[]) {
  let state: 'top' | 'down' = 'top'
  let reps = 0
  frames.forEach((frame) => {
    const knee = (frame.angles.leftKnee + frame.angles.rightKnee) / 2
    if (state === 'top' && knee < 112) state = 'down'
    if (state === 'down' && knee > 154) {
      reps += 1
      state = 'top'
    }
  })
  return reps
}

function countGaitCycles(frames: FrameMetric[]) {
  const signal = frames.map((frame) => frame.leftAnkleX - frame.rightAnkleX)
  let cycles = 0
  for (let i = 1; i < signal.length; i += 1) {
    if (signal[i - 1] <= 0 && signal[i] > 0) cycles += 1
  }
  return cycles
}

export function landmarksToMetric(landmarks: NormalizedLandmark[], timestampMs: number): FrameMetric | null {
  const required = Object.values(L)
  const visible = required.map((index) => landmarks[index]?.visibility ?? 0)
  const visibility = avg(visible)
  if (visibility < 0.45) return null

  const leftHip = landmarks[L.leftHip]
  const rightHip = landmarks[L.rightHip]
  const leftKnee = landmarks[L.leftKnee]
  const rightKnee = landmarks[L.rightKnee]
  const leftAnkle = landmarks[L.leftAnkle]
  const rightAnkle = landmarks[L.rightAnkle]
  const leftShoulder = landmarks[L.leftShoulder]
  const rightShoulder = landmarks[L.rightShoulder]
  const hipCenter = midpoint(leftHip, rightHip)

  const angles: JointAngles = {
    leftKnee: angle(leftHip, leftKnee, leftAnkle),
    rightKnee: angle(rightHip, rightKnee, rightAnkle),
    leftHip: angle(leftShoulder, leftHip, leftKnee),
    rightHip: angle(rightShoulder, rightHip, rightKnee),
    trunkLean: trunkLean(leftShoulder, rightShoulder, leftHip, rightHip),
  }

  const ankleSpread = Math.abs(leftAnkle.x - rightAnkle.x)
  const kneeSpread = Math.abs(leftKnee.x - rightKnee.x)
  const kneeValgusIndex = ankleSpread > 0.02 ? clamp((ankleSpread - kneeSpread) / ankleSpread, 0, 1) : 0

  return {
    timestampMs,
    visibility,
    angles,
    kneeValgusIndex,
    hipCenterX: hipCenter.x,
    hipCenterY: hipCenter.y,
    ankleSpread,
    kneeSpread,
    leftAnkleX: leftAnkle.x,
    rightAnkleX: rightAnkle.x,
  }
}

export function buildEvaluation(frames: FrameMetric[], actionType: ActionType, mode: DetectionMode): EvaluationPayload {
  const durationSec = frames.length
    ? Math.max(0.1, (frames[frames.length - 1].timestampMs - frames[0].timestampMs) / 1000)
    : 0
  const kneeAngles = frames.flatMap((frame) => [frame.angles.leftKnee, frame.angles.rightKnee])
  const hipAngles = frames.flatMap((frame) => [frame.angles.leftHip, frame.angles.rightHip])
  const kneeFlexion = kneeAngles.map((value) => 180 - value)
  const hipFlexion = hipAngles.map((value) => 180 - value)
  const kneeSymDiff = frames.map((frame) => Math.abs(frame.angles.leftKnee - frame.angles.rightKnee))
  const trunkLeanValues = frames.map((frame) => frame.angles.trunkLean)
  const hipCenterX = frames.map((frame) => frame.hipCenterX)
  const kneeValgus = frames.map((frame) => frame.kneeValgusIndex)
  const leftKnee = frames.map((frame) => frame.angles.leftKnee)
  const rightKnee = frames.map((frame) => frame.angles.rightKnee)
  const leftHip = frames.map((frame) => frame.angles.leftHip)
  const rightHip = frames.map((frame) => frame.angles.rightHip)
  const leftSwing = max(frames.map((frame) => frame.leftAnkleX)) - min(frames.map((frame) => frame.leftAnkleX))
  const rightSwing = max(frames.map((frame) => frame.rightAnkleX)) - min(frames.map((frame) => frame.rightAnkleX))
  const kneeRom = avg([max(leftKnee) - min(leftKnee), max(rightKnee) - min(rightKnee)])
  const hipRom = avg([max(leftHip) - min(leftHip), max(rightHip) - min(rightHip)])
  const stabilityIndex = clamp(std(hipCenterX) * 500 + std(trunkLeanValues) * 1.4 + avg(kneeValgus) * 25, 0, 100)
  const symmetryScore = clamp(100 - avg(kneeSymDiff) * 3 - Math.abs(leftSwing - rightSwing) * 160)
  const stabilityScore = clamp(100 - stabilityIndex)
  const formScore = actionType === 'squat'
    ? clamp(100 - avg(kneeValgus) * 120 - Math.max(0, avg(trunkLeanValues) - 22) * 2)
    : clamp(100 - Math.abs(leftSwing - rightSwing) * 180 - std(frames.map((frame) => frame.ankleSpread)) * 180)
  const romScore = actionType === 'squat'
    ? clamp(max(kneeFlexion) * 1.15 + max(hipFlexion) * 0.35)
    : clamp(kneeRom * 1.45 + hipRom * 1.2)
  const overall = Math.round(avg([romScore, symmetryScore, stabilityScore, formScore]))

  return {
    actionType,
    mode,
    durationSec: round(durationSec, 1),
    repetitions: actionType === 'squat' ? countSquats(frames) : countGaitCycles(frames),
    frameCount: frames.length,
    summary: {
      kneeFlexionAvg: round(avg(kneeFlexion)),
      kneeFlexionMax: round(max(kneeFlexion)),
      hipFlexionAvg: round(avg(hipFlexion)),
      hipFlexionMax: round(max(hipFlexion)),
      trunkLeanAvg: round(avg(trunkLeanValues)),
      kneeSymmetryDiffAvg: round(avg(kneeSymDiff)),
      kneeValgusIndexAvg: round(avg(kneeValgus), 2),
      stabilityIndex: round(stabilityIndex),
      gaitCycleSymmetry: actionType === 'walk' ? round(symmetryScore) : undefined,
      kneeRangeOfMotion: actionType === 'walk' ? round(kneeRom) : undefined,
      hipRangeOfMotion: actionType === 'walk' ? round(hipRom) : undefined,
      swingAmplitudeDiff: actionType === 'walk' ? round(Math.abs(leftSwing - rightSwing), 3) : undefined,
      rhythmStability: actionType === 'walk' ? round(100 - std(frames.map((frame) => frame.ankleSpread)) * 220) : undefined,
    },
    preliminaryScores: {
      rangeOfMotion: Math.round(romScore),
      symmetry: Math.round(symmetryScore),
      stability: Math.round(stabilityScore),
      form: Math.round(formScore),
      overall,
    },
    privacyNote: '原始视频、摄像头画面和图片帧仅在浏览器端处理，发送到后端的只有结构化评估指标。',
    generatedAt: new Date().toISOString(),
  }
}
