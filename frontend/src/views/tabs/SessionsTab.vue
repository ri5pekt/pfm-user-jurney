<template>
  <div class="sessions-tab">

    <!-- ── Header ─────────────────────────────────────────────── -->
    <div class="header">
      <div class="header-left">
        <h2>Sessions</h2>
        <span class="total">{{ total.toLocaleString() }} total</span>
      </div>
      <div class="header-right">
        <div class="search-wrap">
          <input
            v-model="searchId"
            class="search-input"
            placeholder="Search session ID…"
            @keydown.enter="doSearch"
            @input="onSearchInput"
          />
          <button v-if="searchId" class="search-clear" @click="clearSearch">✕</button>
        </div>
        <select v-model="filterChannel" @change="goTo(1)" class="filter-select">
          <option value="">All channels</option>
          <option value="paid_search">Paid Search</option>
          <option value="paid_shopping">Paid Shopping</option>
          <option value="paid_social">Paid Social</option>
          <option value="paid_other">Paid Other</option>
          <option value="email">Email</option>
          <option value="sms">SMS</option>
          <option value="organic_search">Organic Search</option>
          <option value="organic_shopping">Organic Shopping</option>
          <option value="organic_social">Organic Social</option>
          <option value="referral">Referral</option>
          <option value="direct">Direct</option>
        </select>
        <button
          class="btn-filters"
          :class="{ active: filtersActive }"
          @click="showFilters = !showFilters"
        >
          Filters<span v-if="filtersActive" class="filter-badge">{{ activeFilterCount }}</span>
        </button>
        <button class="btn-refresh" :disabled="loading" @click="load">
          <span :class="{ spin: loading }">↻</span> Refresh
        </button>
      </div>
    </div>

    <!-- ── Filter panel ────────────────────────────────────────── -->
    <div v-if="showFilters" class="filter-panel">
      <div class="fp-row">
        <label class="fp-label">Min pages</label>
        <input
          v-model.number="minPages"
          type="number" min="0" step="1"
          class="fp-number"
          placeholder="Any"
          @change="goTo(1)"
        />
        <span class="fp-hint">Show sessions with at least N pages</span>
      </div>
      <div class="fp-divider" />
      <div class="fp-row">
        <label class="fp-label">Completed orders</label>
        <button
          class="fp-toggle"
          :class="{ on: ordersOnly }"
          @click="ordersOnly = !ordersOnly; goTo(1)"
        >
          <span class="fp-toggle-knob" />
        </button>
        <span class="fp-hint">Only sessions that reached the thank-you page</span>
      </div>
      <button v-if="filtersActive" class="fp-clear" @click="clearFilters">Clear filters</button>
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
            <th>Location</th>
            <th>Channel</th>
            <th>Source</th>
            <th>Placement</th>
            <th>Entry Page</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && sessions.length === 0">
            <td colspan="8" class="state-cell">Loading…</td>
          </tr>
          <tr v-else-if="sessions.length === 0">
            <td colspan="8" class="state-cell">No sessions yet.</td>
          </tr>
          <tr v-for="s in sessions" :key="s.session_id" class="row clickable" @click="openSession(s.session_id)">
            <td class="col-time">{{ formatTime(s.first_seen) }}</td>
            <td class="col-session">{{ s.session_id.slice(0, 8) }}</td>
            <td class="col-pages">{{ s.page_count }}</td>
            <td class="col-location">
              <span v-if="s.country" class="location-cell">
                <img
                  :src="`/flags/${s.country}.png`"
                  :alt="s.country"
                  class="flag-img"
                  @error="(e) => (e.target as HTMLImageElement).style.display = 'none'"
                />
                <span class="location-text">{{ s.city || s.state_name || s.country }}</span>
              </span>
              <span v-else class="soft">—</span>
            </td>
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
import { ref, computed, onMounted, onActivated } from 'vue'
import { useRouter } from 'vue-router'
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
  country:     string | null
  state_name:  string | null
  city:        string | null
}

interface ChannelStat { channel: string; count: string }

const router        = useRouter()
const sessions      = ref<Session[]>([])
const stats         = ref<ChannelStat[]>([])
const total         = ref(0)
const page          = ref(1)
const limit         = 20
const loading       = ref(false)
const filterChannel = ref('')
const searchId      = ref('')
const showFilters   = ref(true)
const minPages      = ref<number | null>(null)
const ordersOnly    = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))
const filtersActive   = computed(() => (minPages.value !== null && minPages.value > 0) || ordersOnly.value)
const activeFilterCount = computed(() => {
  let n = 0
  if (minPages.value && minPages.value > 0) n++
  if (ordersOnly.value) n++
  return n
})

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, limit }
    if (filterChannel.value) params.channel = filterChannel.value
    if (searchId.value.trim()) params.session_id = searchId.value.trim()
    if (minPages.value && minPages.value > 0) params.min_pages = minPages.value
    if (ordersOnly.value) params.orders_only = '1'
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

function openSession(id: string) {
  router.push(`/session/${id}`)
}

function doSearch() {
  goTo(1)
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => goTo(1), 400)
}

function clearSearch() {
  searchId.value = ''
  goTo(1)
}

function clearFilters() {
  minPages.value  = null
  ordersOnly.value = false
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
  sms:              'SMS',
  organic_search:   'Organic Search',
  organic_shopping: 'Organic Shopping',
  organic_social:   'Organic Social',
  referral:         'Referral',
  direct:           'Direct',
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
// Refresh data when navigating back from session detail (keep-alive restore)
onActivated(() => { load(); loadStats() })
</script>

<style scoped>
.sessions-tab { display: flex; flex-direction: column; gap: 1rem; }

/* Header */
.header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .75rem; }
.header-left { display: flex; align-items: baseline; gap: .75rem; }
h2 { font-size: 1rem; font-weight: 600; }
.total { font-size: .8rem; color: var(--soft); }
.header-right { display: flex; gap: .5rem; align-items: center; }

/* Search */
.search-wrap  { position: relative; display: flex; align-items: center; }
.search-input {
  padding: .38rem 1.8rem .38rem .7rem;
  border: 1.5px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-size: .8rem;
  width: 190px;
  transition: border-color .15s;
}
.search-input:focus   { outline: none; border-color: var(--accent); }
.search-input::placeholder { color: var(--soft); }
.search-clear {
  position: absolute; right: .4rem;
  background: none; border: none; cursor: pointer;
  color: var(--soft); font-size: .7rem; line-height: 1;
  padding: 2px 4px; border-radius: 3px;
}
.search-clear:hover { color: var(--text); }

/* Filters button */
.btn-filters {
  display: flex; align-items: center; gap: 5px;
  padding: .38rem .75rem; border-radius: 6px; font-size: .8rem; font-weight: 500;
  cursor: pointer; border: 1.5px solid var(--border);
  background: var(--surface); color: var(--soft); transition: border-color .15s, color .15s;
}
.btn-filters:hover  { border-color: var(--accent); color: var(--accent); }
.btn-filters.active { border-color: var(--accent); color: var(--accent); background: #f0fdfb; }
.filter-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%; font-size: .65rem; font-weight: 700;
  background: var(--accent); color: #fff;
}

/* Filter panel */
.filter-panel {
  display: flex; flex-wrap: wrap; align-items: center; gap: 1rem;
  padding: .85rem 1rem; background: var(--surface);
  border: 1.5px solid var(--accent); border-radius: 10px;
}
.fp-row   { display: flex; align-items: center; gap: .6rem; }
.fp-divider { width: 1px; height: 28px; background: var(--border); flex-shrink: 0; }
.fp-label { font-size: .78rem; font-weight: 600; color: var(--soft); white-space: nowrap; text-transform: uppercase; letter-spacing: .04em; }
.fp-hint  { font-size: .75rem; color: var(--soft); }
.fp-number {
  width: 70px; padding: .35rem .55rem;
  border: 1.5px solid var(--border); border-radius: 6px;
  background: var(--bg); color: var(--text); font-size: .82rem;
}
.fp-number:focus { outline: none; border-color: var(--accent); }

/* Toggle switch */
.fp-toggle {
  position: relative; width: 36px; height: 20px; border-radius: 10px;
  background: var(--border); border: none; cursor: pointer;
  transition: background .2s; padding: 0; flex-shrink: 0;
}
.fp-toggle.on { background: var(--accent); }
.fp-toggle-knob {
  position: absolute; top: 3px; left: 3px;
  width: 14px; height: 14px; border-radius: 50%; background: #fff;
  transition: transform .2s;
}
.fp-toggle.on .fp-toggle-knob { transform: translateX(16px); }

.fp-clear {
  margin-left: auto; padding: .3rem .7rem; border-radius: 6px;
  background: none; border: 1.5px solid var(--border);
  font-size: .78rem; color: var(--soft); cursor: pointer; transition: border-color .15s, color .15s;
}
.fp-clear:hover { border-color: #ef4444; color: #ef4444; }

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
.row.clickable { cursor: pointer; }
.row.clickable:hover { background: #f0fdfb; }
td { padding: .65rem 1rem; vertical-align: middle; }
.state-cell { text-align: center; color: var(--soft); padding: 2.5rem 1rem; font-size: .875rem; }

/* Columns */
.col-time     { color: var(--soft); white-space: nowrap; font-size: .8rem; }
.col-session  { color: var(--accent); font-family: monospace; font-size: .85rem; font-weight: 600; }
.col-pages    { color: var(--soft); font-size: .8rem; text-align: center; }
.col-location { font-size: .8rem; }
.col-source   { color: var(--text); font-size: .82rem; }
.col-placement{ color: var(--soft); font-size: .78rem; }
.col-entry    { color: var(--text); font-size: .8rem; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Location */
.location-cell { display: flex; align-items: center; gap: .35rem; }
.flag-img      { width: 18px; height: 13px; border-radius: 2px; object-fit: cover; flex-shrink: 0; }
.location-text { color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 110px; }
.soft          { color: var(--soft); }

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
