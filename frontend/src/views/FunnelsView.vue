<template>
  <div class="funnels-page">

    <!-- ── Header ──────────────────────────────────────── -->
    <div class="page-header">
      <h1 class="page-title">Funnels</h1>

      <div class="date-bar">
        <!-- Timezone selector -->
        <select v-model="tzId" class="ctrl-tz">
          <option value="IL">🕐 IL</option>
          <option value="NY">🗽 NY</option>
          <option value="UTC">🌐 UTC</option>
        </select>

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
          :timezone="currentZone"
          class="dp-range"
          @update:model-value="onRangePick"
        />
      </div>
    </div>

    <!-- ── Save / Load bar ────────────────────────────── -->
    <div class="save-bar">
      <div class="save-bar-left">
        <select
          v-model="selectedFunnelId"
          class="funnel-select"
          @change="loadFunnel"
          :disabled="savedFunnels.length === 0"
        >
          <option value="">{{ savedFunnels.length ? 'Load saved funnel…' : 'No saved funnels yet' }}</option>
          <option v-for="f in savedFunnels" :key="f.id" :value="f.id">{{ f.name }}</option>
        </select>

        <button
          v-if="selectedFunnelId"
          class="btn-delete-funnel"
          title="Delete this saved funnel"
          @click="deleteFunnel"
        >✕ Delete</button>
      </div>

      <div class="save-bar-right">
        <template v-if="savingName !== null">
          <input
            v-model="savingName"
            class="save-name-input"
            placeholder="Funnel name…"
            @keydown.enter="confirmSave"
            @keydown.escape="savingName = null"
            ref="saveNameInput"
          />
          <button class="btn-save-confirm" @click="confirmSave" :disabled="!savingName.trim()">Save</button>
          <button class="btn-save-cancel" @click="savingName = null">Cancel</button>
        </template>
        <button v-else class="btn-save-funnel" @click="startSave">
          💾 Save funnel
        </button>
      </div>
    </div>

    <!-- ── Filter bars ─────────────────────────────────── -->
    <div class="filter-section">
      <!-- Primary segment -->
      <div class="segment-row">
        <FilterBar
          :filters="primaryFilters"
          variant="primary"
          @update:filters="primaryFilters = $event"
        />
      </div>

      <!-- Compare segment -->
      <div class="segment-row compare-row" v-if="showCompare">
        <span class="compare-label">vs.</span>
        <FilterBar
          :filters="compareFilters"
          variant="compare"
          @update:filters="compareFilters = $event"
        />
        <button class="btn-remove-compare" @click="removeCompare" title="Remove comparison">✕</button>
      </div>

      <!-- Add comparison -->
      <button
        v-if="!showCompare"
        class="btn-compare"
        @click="showCompare = true"
      >
        + Compare with…
      </button>
    </div>

    <!-- ── Two-panel layout ────────────────────────────── -->
    <div class="layout">

      <!-- LEFT: Builder -->
      <div class="panel panel-builder">
        <FunnelBuilder ref="builderRef" @update:steps="onStepsUpdate" />

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

        <FunnelChart
          v-else-if="result"
          :primary="result.primary"
          :compare="result.compare"
        />
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted } from 'vue'
import api from '@/api'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import FunnelBuilder from './funnels/FunnelBuilder.vue'
import FunnelChart   from './funnels/FunnelChart.vue'
import FilterBar     from './funnels/FilterBar.vue'
import type { BuilderStep }  from './funnels/FunnelBuilder.vue'
import type { ActiveFilter } from './funnels/filterTypes'

interface StepResult  { label: string; count: number; pct_prev: number; pct_total: number; drop_off: number }
interface FunnelResult { total: number; overall_conversion: number; steps: StepResult[] }
interface ComputeResponse { primary: FunnelResult; compare?: FunnelResult }

defineOptions({ name: 'FunnelsView' })

/* ── Timezone ─────────────────────────────────────── */
type TzKey = 'IL' | 'NY' | 'UTC'
const ZONES: Record<TzKey, { label: string; iana: string }> = {
  IL:  { label: 'IL',  iana: 'Asia/Jerusalem'   },
  NY:  { label: 'NY',  iana: 'America/New_York'  },
  UTC: { label: 'UTC', iana: 'UTC'               },
}
const tzId        = ref<TzKey>('IL')
const currentZone = computed(() => ZONES[tzId.value].iana)

function tzOffsetMs(zone: string, at: Date = new Date()): number {
  const fmt = (z: string) => at.toLocaleString('en-US', {
    timeZone: z, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  })
  return Date.parse(fmt(zone)) - Date.parse(fmt('UTC'))
}
function startOfDayInZone(zone: string, daysAgo = 0): Date {
  const now  = new Date()
  const off  = tzOffsetMs(zone, now)
  const fake = new Date(now.getTime() + off)
  fake.setUTCHours(0, 0, 0, 0)
  if (daysAgo) fake.setUTCDate(fake.getUTCDate() - daysAgo)
  return new Date(fake.getTime() - off)
}

/* ── Date range ───────────────────────────────────── */
type PresetId = '24h' | '7d' | '30d' | 'custom'
const PRESETS = [
  { id: '24h'    as PresetId, label: '24h'    },
  { id: '7d'     as PresetId, label: '7d'     },
  { id: '30d'    as PresetId, label: '30d'    },
  { id: 'custom' as PresetId, label: 'Custom' },
]
const preset      = ref<PresetId>('7d')
const customRange = ref<[Date, Date]>([startOfDayInZone(currentZone.value, 7), new Date()])

function getRange() {
  const now  = new Date()
  const zone = currentZone.value
  if (preset.value === '24h')  return { start: new Date(now.getTime() - 86_400_000).toISOString(), end: now.toISOString() }
  if (preset.value === '7d')   return { start: startOfDayInZone(zone, 7).toISOString(),  end: now.toISOString() }
  if (preset.value === '30d')  return { start: startOfDayInZone(zone, 30).toISOString(), end: now.toISOString() }
  const [s, e] = customRange.value
  return { start: s?.toISOString() ?? '', end: e?.toISOString() ?? now.toISOString() }
}
function setPreset(id: PresetId) { preset.value = id }
function onRangePick(r: [Date, Date]) { customRange.value = r }

/* ── Filters ──────────────────────────────────────── */
const primaryFilters = ref<ActiveFilter[]>([])
const compareFilters = ref<ActiveFilter[]>([])
const showCompare    = ref(false)

function removeCompare() {
  showCompare.value   = false
  compareFilters.value = []
}

function toApiFilters(filters: ActiveFilter[]) {
  return filters.map(f => ({ field: f.field, operator: f.operator, values: f.values }))
}

/* ── Steps ────────────────────────────────────────── */
const steps   = ref<BuilderStep[]>([])
const loading = ref(false)
const error   = ref('')
const result  = ref<ComputeResponse | null>(null)

function onStepsUpdate(s: BuilderStep[]) { steps.value = s }
const canCompute = computed(() => steps.value.filter(s => s.configured).length >= 2)

/* ── Builder ref ──────────────────────────────────── */
const builderRef = ref<InstanceType<typeof FunnelBuilder> | null>(null)

/* ── Save / Load funnels ──────────────────────────── */
interface SavedFunnelMeta { id: number; name: string; created_by: string | null; created_at: string }
interface SavedFunnelFull extends SavedFunnelMeta { config: Record<string, unknown> }

const savedFunnels    = ref<SavedFunnelMeta[]>([])
const selectedFunnelId = ref<number | ''>('')
const savingName       = ref<string | null>(null)
const saveNameInput    = ref<HTMLInputElement | null>(null)

async function fetchSavedFunnels() {
  try {
    const { data } = await api.get<SavedFunnelMeta[]>('/funnels/saved')
    savedFunnels.value = data
  } catch { /* ignore */ }
}

async function loadFunnel() {
  if (!selectedFunnelId.value) return
  try {
    const { data } = await api.get<SavedFunnelFull>(`/funnels/saved/${selectedFunnelId.value}`)
    const c = data.config
    // Restore steps via builder ref
    if (Array.isArray(c.steps) && builderRef.value) {
      builderRef.value.loadSteps(c.steps as BuilderStep[])
    }
    // Restore filters
    if (Array.isArray(c.primaryFilters)) primaryFilters.value = c.primaryFilters as ActiveFilter[]
    if (Array.isArray(c.compareFilters)) compareFilters.value = c.compareFilters as ActiveFilter[]
    showCompare.value = Boolean(c.showCompare)
    // Restore timezone + preset
    if (c.tzId && ['IL','NY','UTC'].includes(c.tzId as string)) tzId.value = c.tzId as TzKey
    if (c.preset && ['24h','7d','30d','custom'].includes(c.preset as string)) preset.value = c.preset as PresetId
    if (c.preset === 'custom' && Array.isArray(c.customRange) && c.customRange[0] && c.customRange[1]) {
      customRange.value = [new Date(c.customRange[0] as string), new Date(c.customRange[1] as string)]
    }
    // Auto-compute after loading
    await nextTick()
    compute()
  } catch { /* ignore */ }
}

async function deleteFunnel() {
  if (!selectedFunnelId.value) return
  if (!confirm('Delete this saved funnel?')) return
  try {
    await api.delete(`/funnels/saved/${selectedFunnelId.value}`)
    selectedFunnelId.value = ''
    await fetchSavedFunnels()
  } catch { /* ignore */ }
}

function startSave() {
  savingName.value = ''
  nextTick(() => saveNameInput.value?.focus())
}

async function confirmSave() {
  if (!savingName.value?.trim()) return
  const config = {
    steps:          steps.value,
    primaryFilters: primaryFilters.value,
    compareFilters: compareFilters.value,
    showCompare:    showCompare.value,
    preset:         preset.value,
    tzId:           tzId.value,
    customRange:    preset.value === 'custom' ? customRange.value.map(d => d?.toISOString() ?? null) : [null, null],
  }
  try {
    await api.post('/funnels/saved', { name: savingName.value.trim(), config })
    savingName.value = null
    await fetchSavedFunnels()
  } catch { /* ignore */ }
}

onMounted(fetchSavedFunnels)

/* ── Compute ──────────────────────────────────────── */
async function compute() {
  error.value   = ''
  loading.value = true
  result.value  = null

  const range      = getRange()
  const configured = steps.value.filter(s => s.configured)

  const body: Record<string, unknown> = {
    steps:   configured.map(s => ({ type: s.type, url_match: s.url_match, url_value: s.url_value, event_type: s.event_type, label: s.label })),
    filters: toApiFilters(primaryFilters.value),
    start:   range.start,
    end:     range.end,
  }
  if (showCompare.value) {
    body.compare = toApiFilters(compareFilters.value)
  }

  try {
    const { data } = await api.post<ComputeResponse>('/funnels/compute', body)
    result.value = data
  } catch (e: unknown) {
    error.value = (e as { response?: { data?: { error?: string } } })?.response?.data?.error ?? 'Failed to compute funnel'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.funnels-page { display: flex; flex-direction: column; gap: .75rem; height: calc(100vh - 130px); }

/* Header */
.page-header { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; flex-wrap: wrap; gap: .6rem; }
.page-title  { font-size: 1.25rem; font-weight: 700; margin: 0; }
.date-bar    { display: flex; align-items: center; gap: .35rem; flex-wrap: wrap; }
.ctrl-tz {
  padding: .28rem .55rem; font-size: .8rem; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--border); color: var(--text);
  cursor: pointer; height: 28px;
}
.ctrl-tz:focus { outline: none; border-color: var(--accent); }

.preset-btn  {
  padding: .28rem .7rem; font-size: .8rem; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--border); color: var(--soft); cursor: pointer;
}
.preset-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.preset-btn:not(.active):hover { border-color: var(--accent); color: var(--accent); }
.dp-range { width: 200px; font-size: .78rem; }
.dp-range :deep(.dp__input) {
  padding: .28rem .5rem .28rem 2rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: .78rem; height: auto; min-height: unset;
}

/* Save / Load bar */
.save-bar {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: .5rem; flex-shrink: 0;
}
.save-bar-left, .save-bar-right { display: flex; align-items: center; gap: .4rem; }

.funnel-select {
  padding: .28rem .55rem; font-size: .8rem; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--border); color: var(--text);
  cursor: pointer; max-width: 240px;
}
.funnel-select:focus { outline: none; border-color: var(--accent); }

.btn-delete-funnel {
  padding: .26rem .6rem; font-size: .75rem; border-radius: 6px;
  background: none; border: 1px solid #fca5a5; color: #ef4444; cursor: pointer;
}
.btn-delete-funnel:hover { background: #fef2f2; }

.btn-save-funnel {
  padding: .28rem .7rem; font-size: .8rem; font-weight: 600; border-radius: 6px;
  background: var(--accent); border: none; color: #fff; cursor: pointer;
}
.btn-save-funnel:hover { opacity: .88; }

.save-name-input {
  padding: .28rem .6rem; font-size: .8rem; border-radius: 6px;
  background: var(--surface); border: 1px solid var(--accent); color: var(--text);
  outline: none; width: 180px;
}
.btn-save-confirm {
  padding: .28rem .65rem; font-size: .8rem; font-weight: 600; border-radius: 6px;
  background: var(--accent); border: none; color: #fff; cursor: pointer;
}
.btn-save-confirm:disabled { opacity: .4; cursor: not-allowed; }
.btn-save-cancel {
  padding: .28rem .55rem; font-size: .8rem; border-radius: 6px;
  background: none; border: 1px solid var(--border); color: var(--soft); cursor: pointer;
}
.btn-save-cancel:hover { border-color: var(--text); color: var(--text); }

/* Filter section */
.filter-section {
  flex-shrink: 0;
  display: flex; flex-direction: column; gap: .4rem;
  padding: .6rem .85rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
}

.segment-row {
  display: flex; align-items: center; gap: .5rem; flex-wrap: wrap;
}

.compare-row {
  padding-top: .4rem;
  border-top: 1px solid var(--border);
}

.compare-label {
  font-size: .72rem; font-weight: 700; color: var(--soft);
  text-transform: uppercase; letter-spacing: .04em; flex-shrink: 0;
}

.btn-remove-compare {
  background: none; border: none; cursor: pointer;
  font-size: .8rem; color: var(--soft); padding: 0 .2rem;
  margin-left: auto;
}
.btn-remove-compare:hover { color: #ef4444; }

.btn-compare {
  align-self: flex-start;
  padding: .2rem .55rem; font-size: .74rem; font-weight: 500;
  background: none; border: 1px dashed var(--border);
  border-radius: 20px; color: var(--soft); cursor: pointer;
}
.btn-compare:hover { border-color: #f43f5e; color: #f43f5e; border-style: solid; }

/* Layout */
.layout {
  flex: 1; display: grid; grid-template-columns: 380px 1fr;
  gap: 1rem; overflow: hidden; min-height: 0;
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
.placeholder { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.5rem; }
.placeholder-bars { display: flex; align-items: flex-end; gap: 1rem; }
.ph-bar { width: 60px; background: var(--accent); border-radius: 6px 6px 0 0; }
.placeholder-hint { font-size: .88rem; color: var(--soft); text-align: center; line-height: 1.5; }

/* Loading */
.center-msg { height: 100%; display: flex; align-items: center; justify-content: center; gap: .6rem; font-size: .9rem; color: var(--soft); }
.spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #e2e8f0; border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }
</style>
