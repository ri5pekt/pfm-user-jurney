<template>
  <div class="funnels-page">

    <!-- ── Header ───────────────────────────────────── -->
    <div class="page-header">
      <h1 class="page-title">Funnels</h1>

      <!-- Date range controls -->
      <div class="date-bar">
        <button
          v-for="p in PRESETS"
          :key="p.id"
          class="preset-btn"
          :class="{ active: preset === p.id }"
          @click="setPreset(p.id)"
        >{{ p.label }}</button>

        <VueDatePicker
          v-if="preset === 'custom'"
          v-model="customRange"
          range
          :enable-time-picker="true"
          auto-apply
          :close-on-auto-apply="true"
          format="MM/dd HH:mm"
          class="dp-range"
          @update:model-value="onRangePick"
        />
      </div>
    </div>

    <!-- ── Two-panel layout ──────────────────────────── -->
    <div class="layout">

      <!-- LEFT: Builder -->
      <div class="panel panel-builder">
        <FunnelBuilder @update:steps="onStepsUpdate" />

        <!-- Compute button -->
        <button
          class="btn-compute"
          :disabled="!canCompute || loading"
          @click="compute"
        >
          <span v-if="loading" class="spinner" />
          {{ loading ? 'Computing…' : 'Compute Funnel' }}
        </button>

        <p v-if="error" class="error-msg">{{ error }}</p>
      </div>

      <!-- RIGHT: Results -->
      <div class="panel panel-result">
        <!-- Placeholder before first compute -->
        <div v-if="!result && !loading" class="placeholder">
          <div class="placeholder-bars">
            <div class="ph-bar" style="height:90px;opacity:.7" />
            <div class="ph-bar" style="height:65px;opacity:.5" />
            <div class="ph-bar" style="height:40px;opacity:.35" />
            <div class="ph-bar" style="height:20px;opacity:.2" />
          </div>
          <p class="placeholder-hint">Configure steps and click<br><strong>Compute Funnel</strong></p>
        </div>

        <div v-else-if="loading" class="center-msg">
          <span class="spinner" /> Computing…
        </div>

        <FunnelChart v-else-if="result" :result="result" />
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import api from '@/api'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import FunnelBuilder from './funnels/FunnelBuilder.vue'
import FunnelChart   from './funnels/FunnelChart.vue'
import type { BuilderStep } from './funnels/FunnelBuilder.vue'

interface StepResult {
  label: string; count: number; pct_prev: number; pct_total: number; drop_off: number
}
interface FunnelResult {
  total: number; overall_conversion: number; steps: StepResult[]
}

defineOptions({ name: 'FunnelsView' })

/* ── Date range ───────────────────────────────────── */
type PresetId = '24h' | '7d' | '30d' | 'custom'
const PRESETS = [
  { id: '24h'   as PresetId, label: '24h'    },
  { id: '7d'    as PresetId, label: '7d'     },
  { id: '30d'   as PresetId, label: '30d'    },
  { id: 'custom'as PresetId, label: 'Custom' },
]

const preset      = ref<PresetId>('7d')
const customRange = ref<[Date, Date]>([startOfDay(7), new Date()])

function startOfDay(daysAgo = 0): Date {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  d.setHours(0, 0, 0, 0)
  return d
}

function getRange(): { start: string; end: string } {
  const now = new Date()
  if (preset.value === '24h')  return { start: new Date(now.getTime() - 86_400_000).toISOString(), end: now.toISOString() }
  if (preset.value === '7d')   return { start: startOfDay(7).toISOString(),  end: now.toISOString() }
  if (preset.value === '30d')  return { start: startOfDay(30).toISOString(), end: now.toISOString() }
  const [s, e] = customRange.value
  return { start: s?.toISOString() ?? '', end: e?.toISOString() ?? now.toISOString() }
}

function setPreset(id: PresetId) { preset.value = id }
function onRangePick(r: [Date, Date]) { customRange.value = r }

/* ── Steps ────────────────────────────────────────── */
const steps   = ref<BuilderStep[]>([])
const loading = ref(false)
const error   = ref('')
const result  = ref<FunnelResult | null>(null)

function onStepsUpdate(s: BuilderStep[]) { steps.value = s }

const canCompute = computed(() =>
  steps.value.filter(s => s.configured).length >= 2
)

/* ── Compute ──────────────────────────────────────── */
async function compute() {
  error.value  = ''
  loading.value = true
  result.value  = null

  const range     = getRange()
  const configured = steps.value.filter(s => s.configured)

  try {
    const { data } = await api.post('/funnels/compute', {
      steps:   configured.map(s => ({
        type:       s.type,
        url_match:  s.url_match,
        url_value:  s.url_value,
        event_type: s.event_type,
        label:      s.label,
      })),
      filters: [],
      start:   range.start,
      end:     range.end,
    })
    result.value = data
  } catch (e: unknown) {
    error.value = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? 'Failed to compute funnel'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.funnels-page { display: flex; flex-direction: column; gap: 1rem; height: calc(100vh - 130px); }

/* Header */
.page-header {
  display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; flex-wrap: wrap; gap: .6rem;
}
.page-title { font-size: 1.25rem; font-weight: 700; margin: 0; }

.date-bar { display: flex; align-items: center; gap: .35rem; flex-wrap: wrap; }
.preset-btn {
  padding: .28rem .7rem; font-size: .8rem; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--soft); cursor: pointer;
}
.preset-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.preset-btn:not(.active):hover { border-color: var(--accent); color: var(--accent); }

.dp-range { width: 200px; font-size: .78rem; }
.dp-range :deep(.dp__input) {
  padding: .28rem .5rem .28rem 2rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); font-size: .78rem; height: auto; min-height: unset;
}

/* Two-panel layout */
.layout {
  flex: 1; display: grid; grid-template-columns: 380px 1fr;
  gap: 1rem; overflow: hidden;
}

.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 1.25rem; overflow-y: auto;
}
.panel-builder { display: flex; flex-direction: column; gap: 1rem; }

/* Compute button */
.btn-compute {
  padding: .55rem 1.2rem; font-size: .88rem; font-weight: 600;
  background: var(--accent); border: none; border-radius: 8px;
  color: #fff; cursor: pointer; display: flex; align-items: center; gap: .5rem;
  align-self: flex-start;
}
.btn-compute:disabled { opacity: .45; cursor: not-allowed; }
.btn-compute:not(:disabled):hover { opacity: .88; }

.error-msg { font-size: .8rem; color: #ef4444; margin: 0; }

/* Placeholder */
.placeholder {
  height: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 1.5rem;
}
.placeholder-bars {
  display: flex; align-items: flex-end; gap: 1rem;
}
.ph-bar {
  width: 60px; background: var(--accent); border-radius: 6px 6px 0 0;
}
.placeholder-hint { font-size: .88rem; color: var(--soft); text-align: center; line-height: 1.5; }

/* Loading */
.center-msg {
  height: 100%; display: flex; align-items: center; justify-content: center;
  gap: .6rem; font-size: .9rem; color: var(--soft);
}
.spinner {
  display: inline-block; width: 16px; height: 16px;
  border: 2px solid #e2e8f0; border-top-color: var(--accent);
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }
</style>
