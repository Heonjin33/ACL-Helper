<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import {
  Activity,
  BarChart3,
  Camera,
  CheckCircle2,
  Download,
  FileVideo,
  Loader2,
  Mic,
  Play,
  ShieldCheck,
  Square,
  Trash2,
  Upload,
} from 'lucide-vue-next'
import { drawPose, getPoseLandmarker } from './composables/usePoseLandmarker'
import { createReport, pdfUrl } from './services/api'
import { clearHistory, loadHistory, saveHistory } from './services/storage'
import type { ActionType, DetectionMode, EvaluationPayload, FrameMetric, HistoryRecord, ReportResponse } from './types'
import { buildEvaluation, landmarksToMetric } from './utils/poseMath'

const actionType = ref<ActionType>('squat')
const mode = ref<DetectionMode>('upload')
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const videoUrl = ref('')
const fileName = ref('')
const status = ref('请选择动作类型和检测方式。')
const isLoadingModel = ref(false)
const isDetecting = ref(false)
const isGenerating = ref(false)
const frames = ref<FrameMetric[]>([])
const latestMetric = ref<FrameMetric | null>(null)
const evaluation = ref<EvaluationPayload | null>(null)
const report = ref<ReportResponse | null>(null)
const history = ref<HistoryRecord[]>(loadHistory())
const stream = ref<MediaStream | null>(null)
let rafId = 0

const actionLabel = computed(() => actionType.value === 'squat' ? '深蹲' : '走路')
const canGenerate = computed(() => frames.value.length >= 20 && !isGenerating.value)
const latestAngles = computed(() => latestMetric.value?.angles)
const privacyCopy = computed(() => mode.value === 'camera'
  ? '摄像头画面仅在浏览器端实时处理，不上传服务器。'
  : '上传视频仅在浏览器端逐帧处理，后端不会收到原始视频。')

function resetAnalysis(keepSource = true) {
  frames.value = []
  latestMetric.value = null
  evaluation.value = null
  report.value = null
  if (!keepSource) {
    videoUrl.value = ''
    fileName.value = ''
  }
  const canvas = canvasRef.value
  const ctx = canvas?.getContext('2d')
  if (canvas && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
}

async function ensureModel() {
  isLoadingModel.value = true
  status.value = '正在加载 MediaPipe Pose 模型...'
  try {
    await getPoseLandmarker()
    status.value = '模型已就绪，可以开始检测。'
  } finally {
    isLoadingModel.value = false
  }
}

async function handleUpload(event: Event) {
  stopDetection()
  stopCamera()
  resetAnalysis(false)
  mode.value = 'upload'
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  fileName.value = file.name
  videoUrl.value = URL.createObjectURL(file)
  await nextTick()
  status.value = `已选择 ${file.name}，点击开始检测。`
}

async function startUploadedVideo() {
  if (!videoUrl.value || !videoRef.value) {
    status.value = '请先选择一个走路或深蹲视频。'
    return
  }
  mode.value = 'upload'
  await ensureModel()
  resetAnalysis(true)
  isDetecting.value = true
  await videoRef.value.play()
  status.value = '正在浏览器端分析视频帧...'
  runDetectionLoop()
}

async function startCamera() {
  stopDetection()
  resetAnalysis(false)
  mode.value = 'camera'
  await ensureModel()
  stream.value = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
    audio: false,
  })
  await nextTick()
  if (!videoRef.value) return
  videoRef.value.srcObject = stream.value
  videoRef.value.muted = true
  await videoRef.value.play()
  isDetecting.value = true
  status.value = `正在实时检测${actionLabel.value}动作。${privacyCopy.value}`
  runDetectionLoop()
}

function stopCamera() {
  stream.value?.getTracks().forEach((track) => track.stop())
  stream.value = null
  if (videoRef.value?.srcObject) videoRef.value.srcObject = null
}

function stopDetection() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
  isDetecting.value = false
  videoRef.value?.pause()
  if (frames.value.length) {
    evaluation.value = buildEvaluation(frames.value, actionType.value, mode.value)
    status.value = `已完成 ${frames.value.length} 帧结构化分析，可生成 AI 报告。`
    speak(`检测完成，初步评分 ${evaluation.value.preliminaryScores.overall} 分`)
  }
}

async function runDetectionLoop() {
  const landmarker = await getPoseLandmarker()
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return

  const tick = () => {
    if (!isDetecting.value || !videoRef.value || !canvasRef.value) return
    if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
      const timestamp = performance.now()
      const result = landmarker.detectForVideo(video, timestamp)
      const landmarks = result.landmarks?.[0]
      drawPose(canvas, video, landmarks)
      if (landmarks) {
        const metric = landmarksToMetric(landmarks, timestamp)
        if (metric) {
          latestMetric.value = metric
          frames.value.push(metric)
          if (frames.value.length % 45 === 0) {
            evaluation.value = buildEvaluation(frames.value, actionType.value, mode.value)
          }
        }
      }
    }

    if (mode.value === 'upload' && video.ended) {
      stopDetection()
      return
    }
    rafId = requestAnimationFrame(tick)
  }

  rafId = requestAnimationFrame(tick)
}

async function generateReport() {
  if (!frames.value.length) return
  evaluation.value = buildEvaluation(frames.value, actionType.value, mode.value)
  isGenerating.value = true
  status.value = '正在发送结构化指标给后端生成康复报告...'
  try {
    const response = await createReport(evaluation.value)
    report.value = response
    history.value = saveHistory({
      id: `${Date.now()}`,
      payload: evaluation.value,
      report: response,
    })
    status.value = '报告已生成，并已保存到浏览器本地历史。'
    speak(`报告生成完成，康复评分 ${response.overallScore} 分`)
  } catch (error) {
    status.value = error instanceof Error ? error.message : '报告生成失败'
  } finally {
    isGenerating.value = false
  }
}

function speak(text: string) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'zh-CN'
  utterance.rate = 0.95
  window.speechSynthesis.speak(utterance)
}

function removeHistory() {
  clearHistory()
  history.value = []
}

onBeforeUnmount(() => {
  stopDetection()
  stopCamera()
  if (videoUrl.value) URL.revokeObjectURL(videoUrl.value)
})
</script>

<template>
  <main class="app-shell">
    <section class="top-band">
      <div>
        <p class="eyebrow">ACL-helper</p>
        <h1>十字韧带重建康复动作评估</h1>
        <p class="lead">浏览器端识别走路与深蹲动作，后端只接收结构化指标并生成康复辅助报告。</p>
      </div>
      <div class="disclaimer" role="note">
        <ShieldCheck :size="22" aria-hidden="true" />
        <span>本工具仅用于康复训练辅助评估，不作为正式医学诊断、治疗决策或急症判断依据。</span>
      </div>
    </section>

    <section class="workspace">
      <aside class="control-panel" aria-label="检测控制">
        <div class="section-title">
          <Activity :size="19" aria-hidden="true" />
          <h2>检测设置</h2>
        </div>

        <label class="field-label">动作类型</label>
        <div class="segmented">
          <button :class="{ active: actionType === 'squat' }" @click="actionType = 'squat'; resetAnalysis(true)">
            深蹲
          </button>
          <button :class="{ active: actionType === 'walk' }" @click="actionType = 'walk'; resetAnalysis(true)">
            走路
          </button>
        </div>

        <label class="field-label">检测方式</label>
        <div class="mode-grid">
          <label :class="['mode-card', { active: mode === 'upload' }]">
            <input type="radio" value="upload" v-model="mode" @change="stopCamera(); resetAnalysis(false)">
            <FileVideo :size="22" aria-hidden="true" />
            <span>上传视频检测</span>
          </label>
          <label :class="['mode-card', { active: mode === 'camera' }]">
            <input type="radio" value="camera" v-model="mode" @change="resetAnalysis(false)">
            <Camera :size="22" aria-hidden="true" />
            <span>摄像头实时检测</span>
          </label>
        </div>

        <div v-if="mode === 'upload'" class="upload-box">
          <label class="upload-button">
            <Upload :size="18" aria-hidden="true" />
            <span>{{ fileName || '选择本地视频' }}</span>
            <input type="file" accept="video/*" @change="handleUpload">
          </label>
          <button class="primary" :disabled="!videoUrl || isLoadingModel || isDetecting" @click="startUploadedVideo">
            <Play :size="18" aria-hidden="true" />
            开始检测
          </button>
        </div>

        <div v-else class="upload-box">
          <button class="primary" :disabled="isLoadingModel || isDetecting" @click="startCamera">
            <Camera :size="18" aria-hidden="true" />
            打开摄像头
          </button>
          <p class="helper">实时画面不会离开浏览器。</p>
        </div>

        <button class="secondary" :disabled="!isDetecting" @click="stopDetection">
          <Square :size="17" aria-hidden="true" />
          停止并汇总
        </button>

        <button class="report-button" :disabled="!canGenerate" @click="generateReport">
          <Loader2 v-if="isGenerating" class="spin" :size="18" aria-hidden="true" />
          <BarChart3 v-else :size="18" aria-hidden="true" />
          生成康复报告
        </button>

        <p class="status" aria-live="polite">{{ status }}</p>
      </aside>

      <section class="analysis-area">
        <div class="stage">
          <video
            ref="videoRef"
            class="video"
            :src="mode === 'upload' ? videoUrl : undefined"
            playsinline
            muted
            controls
          />
          <canvas ref="canvasRef" class="overlay" />
          <div v-if="!videoUrl && mode === 'upload'" class="empty-stage">
            <FileVideo :size="42" aria-hidden="true" />
            <span>选择视频后开始浏览器端检测</span>
          </div>
        </div>

        <div class="metrics-strip">
          <div>
            <span>已分析帧</span>
            <strong>{{ frames.length }}</strong>
          </div>
          <div>
            <span>左膝角</span>
            <strong>{{ latestAngles ? latestAngles.leftKnee.toFixed(0) : '--' }}°</strong>
          </div>
          <div>
            <span>右膝角</span>
            <strong>{{ latestAngles ? latestAngles.rightKnee.toFixed(0) : '--' }}°</strong>
          </div>
          <div>
            <span>躯干前倾</span>
            <strong>{{ latestAngles ? latestAngles.trunkLean.toFixed(0) : '--' }}°</strong>
          </div>
        </div>
      </section>

      <aside class="insight-panel" aria-label="评估结果">
        <div class="section-title">
          <CheckCircle2 :size="19" aria-hidden="true" />
          <h2>实时摘要</h2>
        </div>

        <div class="score-ring">
          <span>{{ evaluation?.preliminaryScores.overall ?? '--' }}</span>
          <small>初步评分</small>
        </div>

        <div class="score-list">
          <div><span>关节活动度</span><b>{{ evaluation?.preliminaryScores.rangeOfMotion ?? '--' }}</b></div>
          <div><span>左右对称性</span><b>{{ evaluation?.preliminaryScores.symmetry ?? '--' }}</b></div>
          <div><span>稳定性</span><b>{{ evaluation?.preliminaryScores.stability ?? '--' }}</b></div>
          <div><span>动作标准度</span><b>{{ evaluation?.preliminaryScores.form ?? '--' }}</b></div>
        </div>

        <div class="reference">
          <h3>{{ actionLabel }}参考节律</h3>
          <svg viewBox="0 0 240 130" role="img" :aria-label="`${actionLabel}标准动作参考动画`">
            <g :class="['pose-demo', actionType]">
              <circle cx="120" cy="22" r="13" />
              <line x1="120" y1="35" x2="120" y2="70" />
              <line x1="120" y1="45" x2="92" y2="60" />
              <line x1="120" y1="45" x2="148" y2="60" />
              <line x1="120" y1="70" x2="95" y2="100" />
              <line x1="120" y1="70" x2="150" y2="100" />
              <line x1="95" y1="100" x2="78" y2="120" />
              <line x1="150" y1="100" x2="166" y2="120" />
            </g>
          </svg>
        </div>
      </aside>
    </section>

    <section v-if="report" class="report-panel">
      <div>
        <p class="eyebrow">AI 康复报告</p>
        <h2>{{ report.overallScore }} 分 · {{ actionLabel }}评估结果</h2>
      </div>
      <a class="download-link" :href="pdfUrl(report.pdfUrl)" target="_blank" rel="noreferrer">
        <Download :size="18" aria-hidden="true" />
        下载 PDF
      </a>
      <p class="report-text">{{ report.reportText }}</p>
      <div class="report-columns">
        <div>
          <h3>风险提示</h3>
          <ul>
            <li v-for="item in report.riskTips" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div>
          <h3>下一阶段建议</h3>
          <ul>
            <li v-for="item in report.nextPlan" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="history-panel">
      <div class="history-head">
        <div>
          <p class="eyebrow">localStorage</p>
          <h2>浏览器本地训练记录</h2>
        </div>
        <button class="ghost" :disabled="!history.length" @click="removeHistory">
          <Trash2 :size="17" aria-hidden="true" />
          清空
        </button>
      </div>
      <div v-if="history.length" class="history-grid">
        <article v-for="item in history" :key="item.id" class="history-card">
          <span>{{ item.payload.actionType === 'squat' ? '深蹲' : '走路' }} · {{ item.payload.mode === 'camera' ? '摄像头' : '视频' }}</span>
          <strong>{{ item.report?.overallScore ?? item.payload.preliminaryScores.overall }} 分</strong>
          <small>{{ new Date(item.payload.generatedAt).toLocaleString() }}</small>
        </article>
      </div>
      <p v-else class="helper">还没有本地记录。完成一次检测并生成报告后会保存在这里。</p>
    </section>

    <button class="voice-chip" type="button" @click="speak(status)" aria-label="播报当前状态">
      <Mic :size="16" aria-hidden="true" />
      语音播报
    </button>
  </main>
</template>
