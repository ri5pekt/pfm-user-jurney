<template>
  <div class="sessions-tab">

    <!-- ── Header ─────────────────────────────────────────────── -->
    <div class="header">
      <div class="header-left">
        <h2>Sessions</h2>
        <span class="total">{{ total.toLocaleString() }} total</span>
      </div>
      <div class="header-right">
        <select v-model="filterChannel" @change="goTo(1)" class="filter-select">
          <option value="">All channels</option>
          <option value="paid_search">Paid Search</option>
          <option value="paid_shopping">Paid Shopping</option>
          <option value="paid_social">Paid Social</option>
          <option value="paid_other">Paid Other</option>
          <option value="email">Email</option>
          <option value="organic_search">Organic Search</option>
          <option value="organic_shopping">Organic Shopping</option>
          <option value="organic_social">Organic Social</option>
          <option value="referral">Referral</option>
          <option value="direct">Direct</option>
        </select>
        <button class="btn-refresh" :disabled="loading" @click="load">
          <span :class="{ spin: loading }">↻</span> Refresh
        </button>
      </div>
    </div>

    <!-- ── Stats bar ──────────────────────────────────────────── -->
    <div class="stats-bar" v-if="stats.length">
      <div
        v-for="s in stats"
        :key="s.channel"
        class="stat-pill"
        :class="{ active: filterChannel === s.channel }"
        @click="toggleChannel(s.channel)"
      >
        <span class="pill-label">{{ channelLabel(s.channel) }}</span>
        <span class="pill-count">{{ Number(s.count).toLocaleString() }}</span>
      </div>
    </div>

    <!-- ── Table ──────────────────────────────────────────────── -->
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>First Seen</th>
            <th>Session</th>
            <th>Pages</th>
            <th>Channel</th>
            <th>Source</th>
            <th>Placement</th>
            <th>Entry Page</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && sessions.length === 0">
            <td colspan="7" class="state-cell">Loading…</td>
          </tr>
          <tr v-else-if="sessions.length === 0">
            <td colspan="7" class="state-cell">No sessions yet.</td>
          </tr>
          <tr v-for="s in sessions" :key="s.session_id" class="row">
            <td class="col-time">{{ formatTime(s.first_seen) }}</td>
            <td class="col-session">{{ s.session_id.slice(0, 8) }}</td>
            <td class="col-pages">{{ s.page_count }}</td>
            <td class="col-channel">
              <span class="badge" :class="channelClass(s.channel)">{{ channelLabel(s.channel) }}</span>
            </td>
            <td class="col-source">{{ s.source || '—' }}</td>
            <td class="col-placement">{{ s.placement || '—' }}</td>
            <td class="col-entry">{{ urlPath(s.entry_url) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- ── Pagination ─────────────────────────────────────────── -->
    <div class="pagination" v-if="totalPages > 1 || sessions.length > 0">
      <button :disabled="page === 1" @click="goTo(page - 1)">← Prev</button>
      <span class="page-info">Page {{ page }} of {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="goTo(page + 1)">Next →</button>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import api from '@/api'

interface Session {
  session_id:  string
  first_seen:  string
  last_seen:   string
  entry_url:   string
  source:      string
  medium:      string
  channel:     string
  placement:   string
  campaign_id: string
  page_count:  number
}

interface ChannelStat { channel: string; count: string }

const sessions      = ref<Session[]>([])
const stats         = ref<ChannelStat[]>([])
const total         = ref(0)
const page          = ref(1)
const limit         = 20
const loading       = ref(false)
const filterChannel = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, limit }
    if (filterChannel.value) params.channel = filterChannel.value
    const { data } = await api.get('/sessions', { params })
    sessions.value = data.sessions
    total.value    = data.total
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  const { data } = await api.get('/sessions/stats')
  stats.value = data.by_channel
}

function goTo(n: number) { page.value = n; load() }

function toggleChannel(ch: string) {
  filterChannel.value = filterChannel.value === ch ? '' : ch
  goTo(1)
}

// ── Formatters ──────────────────────────────────────────────────────
function formatTime(ts: string) {
  const d   = new Date(ts)
  const now = new Date()
  const time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  if (d.toDateString() === now.toDateString()) return time
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' ' + time
}

function urlPath(url: string) {
  try { return new URL(url).pathname || '/' } catch { return url.slice(0, 40) }
}

const CHANNEL_LABELS: Record<string, string> = {
  paid_search:      'Paid Search',
  paid_shopping:    'Paid Shopping',
  paid_social:      'Paid Social',
  paid_other:       'Paid Other',
  email:            'Email',
  organic_search:   'Organic Search',
  organic_shopping: 'Organic Shopping',
  organic_social:   'Organic Social',
  referral:         'Referral',
  direct:           'Direct',
  internal:         'Internal',
}

function channelLabel(ch: string) { return CHANNEL_LABELS[ch] || ch || '—' }

function channelClass(ch: string) {
  if (ch.startsWith('paid'))      return 'badge-paid'
  if (ch === 'email')             return 'badge-email'
  if (ch.startsWith('organic'))   return 'badge-organic'
  if (ch === 'direct')            return 'badge-direct'
  return 'badge-other'
}

onMounted(() => { load(); loadStats() })
</script>

<style scoped>
.sessions-tab { display: flex; flex-direction: column; gap: 1rem; }

/* Header */
.header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .75rem; }
.header-left { display: flex; align-items: baseline; gap: .75rem; }
h2 { font-size: 1rem; font-weight: 600; }
.total { font-size: .8rem; color: var(--soft); }
.header-right { display: flex; gap: .5rem; align-items: center; }

.filter-select {
  padding: .38rem .7rem;
  border: 1.5px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: .8rem;
  cursor: pointer;
}
.filter-select:focus { outline: none; border-color: var(--accent); }

.btn-refresh {
  display: flex; align-items: center; gap: 6px;
  padding: .4rem .85rem; border-radius: 6px; font-size: .8rem; font-weight: 500;
  cursor: pointer; border: 1.5px solid var(--border);
  background: var(--surface); color: var(--soft); transition: background .15s;
}
.btn-refresh:hover:not(:disabled) { background: var(--bg); color: var(--text); }
.btn-refresh:disabled { opacity: .5; cursor: not-allowed; }
.spin { display: inline-block; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Stats bar */
.stats-bar { display: flex; flex-wrap: wrap; gap: .5rem; }
.stat-pill {
  display: flex; align-items: center; gap: .4rem;
  padding: .3rem .7rem; border-radius: 20px;
  border: 1.5px solid var(--border); background: var(--surface);
  font-size: .78rem; cursor: pointer; transition: border-color .15s, background .15s;
}
.stat-pill:hover  { border-color: var(--accent); }
.stat-pill.active { border-color: var(--accent); background: #f0fdfb; }
.pill-label { color: var(--soft); }
.pill-count { font-weight: 600; color: var(--text); }

/* Table */
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
thead tr { background: #f8fafc; border-bottom: 1px solid var(--border); }
th { padding: .65rem 1rem; text-align: left; font-size: .75rem; font-weight: 600; color: var(--soft); text-transform: uppercase; letter-spacing: .04em; }
.row { border-bottom: 1px solid var(--border); transition: background .1s; }
.row:last-child { border-bottom: none; }
.row:hover { background: #f8fafc; }
td { padding: .65rem 1rem; vertical-align: middle; }
.state-cell { text-align: center; color: var(--soft); padding: 2.5rem 1rem; font-size: .875rem; }

/* Columns */
.col-time     { color: var(--soft); white-space: nowrap; font-size: .8rem; }
.col-session  { color: var(--accent); font-family: monospace; font-size: .85rem; font-weight: 600; }
.col-pages    { color: var(--soft); font-size: .8rem; text-align: center; }
.col-source   { color: var(--text); font-size: .82rem; }
.col-placement{ color: var(--soft); font-size: .78rem; }
.col-entry    { color: var(--text); font-size: .8rem; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Badges */
.badge { display: inline-block; padding: .18rem .55rem; border-radius: 4px; font-size: .73rem; font-weight: 600; white-space: nowrap; }
.badge-paid    { background: #eff6ff; color: #2563eb; }
.badge-email   { background: #fdf4ff; color: #9333ea; }
.badge-organic { background: #f0fdf4; color: #16a34a; }
.badge-direct  { background: #f8fafc; color: var(--soft); }
.badge-other   { background: #fff7ed; color: #c2410c; }

/* Pagination */
.pagination { display: flex; align-items: center; justify-content: center; gap: 1rem; }
.pagination button { padding: .4rem 1rem; border: 1.5px solid var(--border); border-radius: 6px; background: var(--surface); color: var(--text); font-size: .8rem; font-weight: 500; cursor: pointer; transition: border-color .15s; }
.pagination button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.pagination button:disabled { opacity: .4; cursor: not-allowed; }
.page-info { font-size: .8rem; color: var(--soft); }
</style>
