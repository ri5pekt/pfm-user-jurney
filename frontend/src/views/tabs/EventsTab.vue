<template>
  <div class="events-tab">

    <!-- ── Header ─────────────────────────────────────────────── -->
    <div class="header">
      <div class="header-left">
        <h2>Live Events</h2>
        <span class="total">{{ total.toLocaleString() }} total</span>
      </div>
      <div class="header-right">
        <button class="btn-live" :class="{ on: live }" @click="toggleLive">
          <span class="live-dot" />
          {{ live ? 'Live' : 'Paused' }}
        </button>
        <button class="btn-refresh" :disabled="loading" @click="load">
          <span :class="{ spin: loading }">↻</span> Refresh
        </button>
      </div>
    </div>

    <!-- ── Event type filter pills ─────────────────────────────── -->
    <div class="type-pills">
      <button
        v-for="t in EVENT_TYPES"
        :key="t.value"
        class="type-pill"
        :class="[t.cls, { active: filterType === t.value }]"
        @click="toggleType(t.value)"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- ── Table ──────────────────────────────────────────────── -->
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Session</th>
            <th>Event</th>
            <th>Page</th>
            <th>From</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && events.length === 0">
            <td colspan="5" class="state-cell">Loading…</td>
          </tr>
          <tr v-else-if="events.length === 0">
            <td colspan="5" class="state-cell">No events yet. Deploy the tracking script to start collecting.</td>
          </tr>
          <tr v-for="ev in events" :key="ev.id" class="row">
            <td class="col-time">{{ formatTime(ev.timestamp) }}</td>
            <td class="col-session">{{ ev.session_id.slice(0, 8) }}</td>
            <td class="col-event">
              <span class="event-badge" :class="eventClass(ev.event_type)">{{ eventLabel(ev.event_type) }}</span>
            </td>
            <td class="col-page">{{ urlPath(ev.page_url) }}</td>
            <td class="col-ref">{{ refDomain(ev.referrer) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Pagination ─────────────────────────────────────────── -->
    <div class="pagination" v-if="totalPages > 1 || events.length > 0">
      <button :disabled="page === 1" @click="goTo(page - 1)">← Prev</button>
      <span class="page-info">Page {{ page }} of {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="goTo(page + 1)">Next →</button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '@/api'

interface Event {
  id:          number
  session_id:  string
  event_type:  string
  page_url:    string
  referrer:    string
  timestamp:   string
}

const EVENT_TYPES = [
  { value: 'page_view',       label: 'Page View',       cls: 'pill-pageview' },
  { value: 'order_completed', label: 'Order Completed', cls: 'pill-order'    },
  { value: 'add_to_cart',     label: 'Add to Cart',     cls: 'pill-cart'     },
  { value: 'ppu_accepted',    label: 'PPU Accepted',    cls: 'pill-ppu'      },
  { value: 'fp_collected',    label: 'FP Collected',    cls: 'pill-fp'       },
]

const events     = ref<Event[]>([])
const total      = ref(0)
const page       = ref(1)
const limit      = 20
const loading    = ref(false)
const live       = ref(false)
const filterType = ref('')
let   liveTimer  = 0

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, limit }
    if (filterType.value) params.event_type = filterType.value
    const { data } = await api.get('/events', { params })
    events.value = data.events
    total.value  = data.total
  } finally {
    loading.value = false
  }
}

function toggleType(type: string) {
  filterType.value = filterType.value === type ? '' : type
  goTo(1)
}

function goTo(n: number) {
  page.value = n
  load()
}

function toggleLive() {
  live.value = !live.value
  if (live.value) {
    liveTimer = window.setInterval(() => {
      if (page.value === 1) load()
    }, 5000)
  } else {
    clearInterval(liveTimer)
  }
}

// ── Formatters ───────────────────────────────────────────────────────────────

function formatTime(ts: string): string {
  const d   = new Date(ts)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  if (sameDay) return time
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' ' + time
}

function urlPath(url: string): string {
  try { return new URL(url).pathname || '/' }
  catch { return url.slice(0, 40) }
}

function eventLabel(type: string): string {
  if (!type || type === 'page_view') return 'Page View'
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function eventClass(type: string): string {
  if (!type || type === 'page_view') return 'ev-pageview'
  if (type === 'order_completed')    return 'ev-order'
  if (type === 'add_to_cart')        return 'ev-cart'
  if (type === 'ppu_accepted')       return 'ev-ppu'
  return 'ev-custom'
}

function refDomain(url: string): string {
  if (!url) return 'Direct'
  try {
    const u = new URL(url)
    const host = u.hostname.replace(/^www\./, '')
    // Same-site referrer = internal navigation, show path
    if (/particleformen/.test(host)) {
      return u.pathname === '/' ? host : u.pathname
    }
    const path = u.pathname === '/' ? '' : u.pathname
    return host + path
  }
  catch { return url.slice(0, 60) }
}

onMounted(load)
onUnmounted(() => clearInterval(liveTimer))
</script>

<style scoped>
.events-tab {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Header */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.header-left { display: flex; align-items: baseline; gap: 0.75rem; }

h2 { font-size: 1rem; font-weight: 600; }

.total {
  font-size: 0.8rem;
  color: var(--soft);
}

.header-right { display: flex; gap: 0.5rem; }

/* Buttons */
.btn-live, .btn-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--soft);
}

.btn-live.on {
  background: #f0fdfb;
  border-color: var(--accent);
  color: var(--accent);
}

.btn-refresh:hover:not(:disabled) { background: var(--bg); color: var(--text); }
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

/* Live dot */
.live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--soft);
  display: inline-block;
}
.btn-live.on .live-dot {
  background: var(--accent);
  animation: pulse 1.4s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}

/* Spin */
.spin { display: inline-block; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Event type pills */
.type-pills { display: flex; flex-wrap: wrap; gap: .4rem; }
.type-pill {
  padding: .28rem .7rem;
  border-radius: 20px;
  border: 1.5px solid var(--border);
  background: var(--surface);
  font-size: .78rem; font-weight: 600;
  cursor: pointer;
  transition: border-color .15s, background .15s, color .15s;
  color: var(--soft);
}
.type-pill:hover  { border-color: var(--accent); color: var(--accent); }
.type-pill.active { background: #f0fdfb; border-color: var(--accent); color: var(--accent); }

.pill-pageview.active { background: #f8fafc; border-color: var(--soft); color: var(--text); }
.pill-pageview:hover  { border-color: var(--soft); color: var(--text); }
.pill-order.active    { background: #f0fdf4; border-color: #16a34a; color: #16a34a; }
.pill-order:hover     { border-color: #16a34a; color: #16a34a; }
.pill-cart.active     { background: #fff7ed; border-color: #ea580c; color: #ea580c; }
.pill-cart:hover      { border-color: #ea580c; color: #ea580c; }
.pill-ppu.active      { background: #eff6ff; border-color: #2563eb; color: #2563eb; }
.pill-ppu:hover       { border-color: #2563eb; color: #2563eb; }
.pill-fp.active       { background: #eff6ff; border-color: #2563eb; color: #2563eb; }
.pill-fp:hover        { border-color: #2563eb; color: #2563eb; }

/* Table */
.table-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

thead tr {
  background: #f8fafc;
  border-bottom: 1px solid var(--border);
}

th {
  padding: 0.65rem 1rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--soft);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.row { border-bottom: 1px solid var(--border); transition: background 0.1s; }
.row:last-child { border-bottom: none; }
.row:hover { background: #f8fafc; }

td { padding: 0.7rem 1rem; vertical-align: middle; }

.state-cell {
  text-align: center;
  color: var(--soft);
  padding: 2.5rem 1rem;
  font-size: 0.875rem;
}

/* Column styles */
.col-time    { color: var(--soft); white-space: nowrap; font-size: 0.8rem; }
.col-session { color: var(--accent); font-family: monospace; font-size: 0.85rem; font-weight: 600; }
.col-event   { white-space: nowrap; }
.col-page    { color: var(--text); max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-ref     { color: var(--soft); font-size: 0.8rem; }

/* Event badges */
.event-badge {
  display: inline-block;
  padding: .18rem .5rem;
  border-radius: 4px;
  font-size: .72rem;
  font-weight: 600;
  white-space: nowrap;
}
.ev-pageview { background: #f8fafc; color: var(--soft); }
.ev-order    { background: #f0fdf4; color: #16a34a; }
.ev-cart     { background: #fff7ed; color: #ea580c; }
.ev-ppu      { background: #eff6ff; color: #2563eb; }
.ev-custom   { background: #fdf4ff; color: #9333ea; }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

.pagination button {
  padding: 0.4rem 1rem;
  border: 1.5px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.15s;
}

.pagination button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }

.page-info { font-size: 0.8rem; color: var(--soft); }
</style>
