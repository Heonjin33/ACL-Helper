import { FilesetResolver, PoseLandmarker, type NormalizedLandmark } from '@mediapipe/tasks-vision'

const WASM_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm'
const MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task'

const POSE_CONNECTIONS: Array<[number, number]> = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24], [23, 25], [25, 27],
  [24, 26], [26, 28], [27, 29], [29, 31], [28, 30],
  [30, 32], [15, 17], [16, 18], [15, 19], [16, 20],
]

let instance: PoseLandmarker | null = null

export async function getPoseLandmarker() {
  if (instance) return instance
  const vision = await FilesetResolver.forVisionTasks(WASM_URL)
  instance = await PoseLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: MODEL_URL,
      delegate: 'GPU',
    },
    runningMode: 'VIDEO',
    numPoses: 1,
    minPoseDetectionConfidence: 0.5,
    minPosePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  })
  return instance
}

export function drawPose(canvas: HTMLCanvasElement, source: HTMLVideoElement, landmarks?: NormalizedLandmark[]) {
  const rect = source.getBoundingClientRect()
  const width = source.videoWidth || Math.round(rect.width)
  const height = source.videoHeight || Math.round(rect.height)
  if (!width || !height) return

  if (canvas.width !== width) canvas.width = width
  if (canvas.height !== height) canvas.height = height

  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  if (!landmarks?.length) return

  ctx.save()
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = 'rgba(26, 115, 232, 0.9)'
  ctx.lineWidth = Math.max(3, width * 0.004)

  POSE_CONNECTIONS.forEach(([start, end]) => {
    const a = landmarks[start]
    const b = landmarks[end]
    if (!a || !b || (a.visibility ?? 1) < 0.35 || (b.visibility ?? 1) < 0.35) return
    ctx.beginPath()
    ctx.moveTo(a.x * width, a.y * height)
    ctx.lineTo(b.x * width, b.y * height)
    ctx.stroke()
  })

  landmarks.forEach((point, index) => {
    if ((point.visibility ?? 1) < 0.35 || index > 32) return
    ctx.beginPath()
    ctx.fillStyle = index >= 23 && index <= 32 ? '#19a974' : '#2454d6'
    ctx.arc(point.x * width, point.y * height, Math.max(4, width * 0.005), 0, Math.PI * 2)
    ctx.fill()
    ctx.lineWidth = 2
    ctx.strokeStyle = '#ffffff'
    ctx.stroke()
  })

  ctx.restore()
}
