<template>
  <div class="overview-tab">

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="stat" v-if="data">
          {{ rangeLabel }} · {{ data.total.toLocaleString() }} sessions
        </span>
        <span class="live-badge" v-if="isLive">
          <span class="live-dot" :class="{ pulsing: !refreshing }" />
          LIVE
        </span>
        <span class="updated" v-if="isLive && updatedLabel">{{ updatedLabel }}</span>
      </div>
      <div class="toolbar-right">

        <!-- Preset dropdown -->
        <select v-model="preset" class="ctrl-select" @change="onPresetChange">
          <option value="1h">Last hour</option>
          <option value="today">Today</option>
          <option value="yesterday">Yesterday</option>
          <option value="custom">Custom range…</option>
        </select>

        <!-- Custom range inputs (shown only when preset = custom) -->
        <template v-if="preset === 'custom'">
          <input
            v-model="customStart"
            type="datetime-local"
            class="ctrl-dt"
            @change="load"
          />
          <span class="range-arrow">→</span>
          <input
            v-model="customEnd"
            type="datetime-local"
            class="ctrl-dt"
            @change="load"
          />
        </template>

        <button class="btn-reload" @click="load" :disabled="loading">↺</button>
      </div>
    </div>

    <!-- Loading / error -->
    <div class="center-msg" v-if="loading"><span class="spinner" /> Loading…</div>
    <div class="center-msg muted" v-else-if="!data">No sessions in this time range.</div>

    <!-- Widget grid -->
    <div class="grid" v-else>

      <SummaryWidget :data="data" :range-label="rangeLabel" class="widget" />
      <FunnelWidget  :data="data"                           class="widget" />

      <BarChartWidget
        class="widget span-2"
        title="Traffic Sources"
        :items="data.sources"
        color="#3b82f6"
        :top-n="20"
        :show-conversions="true"
      />

      <BarChartWidget
        class="widget"
        title="Landing Pages"
        :items="data.landingPages"
        color="#8b5cf6"
        :top-n="10"
      />
      <BarChartWidget
        class="widget"
        title="Product Pages"
        :items="data.productPages"
        color="#06b6d4"
        :top-n="10"
      />

      <CountriesWidget
        class="widget"
        :items="data.countries"
        :top-n="15"
      />

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, onDeactivated, onUnmounted } from 'vue'
import api from '@/api/index'
import type { FunnelData } from './overview/types'
import SummaryWidget   from './overview/SummaryWidget.vue'
import FunnelWidget    from './overview/FunnelWidget.vue'
import BarChartWidget  from './overview/BarChartWidget.vue'
import CountriesWidget from './overview/CountriesWidget.vue'

/* ── state ──────────────────────────────────────────────── */
type Preset = '1h' | 'today' | 'yesterday' | 'custom'

const loading     = ref(false)
const refreshing  = ref(false)   // silent background refresh
const preset      = ref<Preset>('today')
const customStart = ref(todayAt('00:00'))
const customEnd   = ref(nowDT())
const data        = ref<FunnelData | null>(null)
const lastUpdated = ref<Date | null>(null)
let   liveTimer   = 0

const LIVE_INTERVAL_MS = 30_000  // refresh every 30 s

const isLive = computed(() => preset.value === '1h' || preset.value === 'today')

/* ── helpers ────────────────────────────────────────────── */
function toDT(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
function nowDT()             { return toDT(new Date()) }
function todayAt(hm: string) {
  const d = new Date(); const [h, m] = hm.split(':').map(Number)
  d.setHours(h, m, 0, 0); return toDT(d)
}

function getRange(): { start: string; end: string } {
  const now = new Date()
  if (preset.value === '1h') {
    return { start: new Date(now.getTime() - 3_600_000).toISOString(), end: now.toISOString() }
  }
  if (preset.value === 'today') {
    const s = new Date(now); s.setHours(0, 0, 0, 0)
    return { start: s.toISOString(), end: now.toISOString() }
  }
  if (preset.value === 'yesterday') {
    const s = new Date(now); s.setDate(s.getDate() - 1); s.setHours(0, 0, 0, 0)
    const e = new Date(s);   e.setHours(23, 59, 59, 999)
    return { start: s.toISOString(), end: e.toISOString() }
  }
  return {
    start: customStart.value ? new Date(customStart.value).toISOString() : '',
    end:   customEnd.value   ? new Date(customEnd.value).toISOString()   : now.toISOString(),
  }
}

const rangeLabel = computed(() => {
  const fmt = (dt: string) =>
    new Date(dt).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  if (preset.value === '1h')        return 'Last hour'
  if (preset.value === 'today')     return 'Today'
  if (preset.value === 'yesterday') return 'Yesterday'
  const s = customStart.value ? fmt(new Date(customStart.value).toISOString()) : '?'
  const e = customEnd.value   ? fmt(new Date(customEnd.value).toISOString())   : '?'
  return `${s} → ${e}`
})

const updatedLabel = computed(() => {
  if (!lastUpdated.value) return ''
  return lastUpdated.value.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
})

/* ── live polling ───────────────────────────────────────── */
function startLive() {
  stopLive()
  if (!isLive.value) return
  liveTimer = window.setInterval(() => silentRefresh(), LIVE_INTERVAL_MS)
}
function stopLive() {
  if (liveTimer) { clearInterval(liveTimer); liveTimer = 0 }
}

/* ── data fetching ──────────────────────────────────────── */
async function fetchData(silent = false) {
  if (silent) { refreshing.value = true }
  else        { loading.value = true; data.value = null }
  try {
    const range = getRange()
    const { data: res } = await api.get<FunnelData>('/overview/funnel', {
      params: { start: range.start, end: range.end },
    })
    data.value    = res.total ? res : null
    lastUpdated.value = new Date()
  } finally {
    loading.value   = false
    refreshing.value = false
  }
}

function load()          { fetchData(false) }
function silentRefresh() { fetchData(true)  }

/* ── preset change ──────────────────────────────────────── */
function onPresetChange() {
  stopLive()
  if (preset.value === 'custom') {
    customStart.value = todayAt('00:00')
    customEnd.value   = nowDT()
  } else {
    fetchData(false).then(() => startLive())
  }
}

/* ── lifecycle ──────────────────────────────────────────── */
onMounted(()      => { fetchData(false).then(() => startLive()) })
onActivated(()    => { if (!data.value && !loading.value) fetchData(false).then(() => startLive()); else startLive() })
onDeactivated(()  => { stopLive() })
onUnmounted(()    => { stopLive() })
</script>

<style scoped>
/* ── Tab shell ───────────────────────────────────────── */
.overview-tab {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 130px);
  gap: 0.75rem;
}

/* ── Toolbar ─────────────────────────────────────────── */
.toolbar {
  display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
}
.toolbar-left  { display: flex; align-items: center; gap: 0.5rem; }
.toolbar-right { display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.stat { font-size: 0.78rem; color: var(--soft); }

.live-badge {
  display: inline-flex; align-items: center; gap: 0.3rem;
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.07em;
  color: #22c55e; background: rgba(34,197,94,0.1);
  border: 1px solid rgba(34,197,94,0.3);
  border-radius: 20px; padding: 0.15rem 0.5rem;
}
.live-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #22c55e; flex-shrink: 0;
}
.live-dot.pulsing { animation: livepulse 2s ease-in-out infinite; }
@keyframes livepulse {
  0%, 100% { opacity: 1;   transform: scale(1);    box-shadow: 0 0 0 0 rgba(34,197,94,0.5); }
  50%       { opacity: 0.7; transform: scale(1.2);  box-shadow: 0 0 0 4px rgba(34,197,94,0); }
}
.updated { font-size: 0.7rem; color: var(--soft); }

.ctrl-select {
  padding: 0.28rem 0.45rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); font-size: 0.8rem; cursor: pointer;
}
.ctrl-dt {
  padding: 0.26rem 0.4rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); font-size: 0.78rem; cursor: pointer;
  /* keep it compact — browser adds its own picker icon */
  width: 162px;
}
.ctrl-dt:focus { outline: none; border-color: var(--accent); }

.range-arrow { font-size: 0.8rem; color: var(--soft); }

.btn-reload {
  padding: 0.28rem 0.6rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); font-size: 0.9rem; cursor: pointer;
  line-height: 1;
}
.btn-reload:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.btn-reload:disabled              { opacity: 0.45; cursor: not-allowed; }

/* ── Widget grid ─────────────────────────────────────── */
.grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-content: start;
  gap: 0.9rem;
  padding-bottom: 1rem;
}
.span-2 { grid-column: span 2; }

.widget {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.1rem;
}

/* ── Loading ─────────────────────────────────────────── */
.center-msg {
  flex: 1; display: flex; align-items: center; justify-content: center;
  gap: 0.6rem; font-size: 0.9rem; color: var(--soft);
}
.center-msg.muted { color: #94a3b8; }
.spinner {
  display: inline-block; width: 18px; height: 18px;
  border: 2px solid #e2e8f0; border-top-color: var(--accent);
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg) } }
</style>
