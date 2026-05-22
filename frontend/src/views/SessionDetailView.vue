<template>
  <div class="detail-page">

    <!-- ── Nav ───────────────────────────────────────────────── -->
    <nav class="nav">
      <div class="nav-brand">
        <span class="dot" />
        PFM Journey Tracker
      </div>
      <button class="nav-logout" @click="handleLogout">Sign out</button>
    </nav>

    <!-- ── Sub-header ─────────────────────────────────────────── -->
    <div class="sub-header">
      <button class="back-btn" @click="$router.back()">← Back to Sessions</button>
      <div class="session-title" v-if="session">
        <span class="session-id-label">Session</span>
        <code class="session-id">{{ session.session_id }}</code>
      </div>
    </div>

    <!-- ── Loading / Error ────────────────────────────────────── -->
    <div v-if="loading" class="state-msg">Loading…</div>
    <div v-else-if="error" class="state-msg error">{{ error }}</div>

    <!-- ── Content ───────────────────────────────────────────── -->
    <div v-else-if="session" class="content">

      <!-- Attribution card -->
      <div class="card">
        <div class="card-title">Attribution</div>
        <div class="attr-grid">
          <div class="attr-row">
            <span class="attr-label">Channel</span>
            <span class="badge" :class="channelClass(session.channel)">{{ channelLabel(session.channel) }}</span>
          </div>
          <div class="attr-row">
            <span class="attr-label">Source</span>
            <span class="attr-value">{{ session.source || '—' }}</span>
          </div>
          <div class="attr-row">
            <span class="attr-label">Medium</span>
            <span class="attr-value">{{ session.medium || '—' }}</span>
          </div>
          <div class="attr-row" v-if="session.placement">
            <span class="attr-label">Placement</span>
            <span class="attr-value">{{ session.placement }}</span>
          </div>
          <div class="attr-row" v-if="session.campaign_id">
            <span class="attr-label">Campaign ID</span>
            <span class="attr-value mono">{{ session.campaign_id }}</span>
          </div>
          <div class="attr-row" v-if="session.utm_source">
            <span class="attr-label">utm_source</span>
            <span class="attr-value mono">{{ session.utm_source }}</span>
          </div>
          <div class="attr-row" v-if="session.utm_medium">
            <span class="attr-label">utm_medium</span>
            <span class="attr-value mono">{{ session.utm_medium }}</span>
          </div>
          <div class="attr-row" v-if="session.utm_campaign">
            <span class="attr-label">utm_campaign</span>
            <span class="attr-value mono">{{ session.utm_campaign }}</span>
          </div>
        </div>
      </div>

      <!-- Session meta card -->
      <div class="card">
        <div class="card-title">Session Info</div>
        <div class="attr-grid">
          <div class="attr-row">
            <span class="attr-label">First Seen</span>
            <span class="attr-value">{{ formatTime(session.first_seen) }}</span>
          </div>
          <div class="attr-row">
            <span class="attr-label">Last Seen</span>
            <span class="attr-value">{{ formatTime(session.last_seen) }}</span>
          </div>
          <div class="attr-row">
            <span class="attr-label">Duration</span>
            <span class="attr-value">{{ duration }}</span>
          </div>
          <div class="attr-row">
            <span class="attr-label">Pages</span>
            <span class="attr-value">{{ session.page_count }}</span>
          </div>
          <div class="attr-row">
            <span class="attr-label">Entry Page</span>
            <a class="attr-link" :href="session.entry_url" target="_blank" rel="noopener">{{ urlPath(session.entry_url) }}</a>
          </div>
          <div class="attr-row" v-if="session.referrer">
            <span class="attr-label">Referrer</span>
            <a class="attr-link" :href="session.referrer" target="_blank" rel="noopener">{{ session.referrer }}</a>
          </div>
          <div class="attr-row" v-else>
            <span class="attr-label">Referrer</span>
            <span class="attr-value soft">Direct / None</span>
          </div>
        </div>
      </div>

      <!-- Journey timeline -->
      <div class="card journey-card">
        <div class="card-title">Journey <span class="event-count">({{ displayEvents.length }} events)</span></div>
        <div class="timeline">
          <div
            v-for="(ev, idx) in displayEvents"
            :key="idx"
            class="timeline-item"
          >
            <div class="tl-left">
              <div class="tl-dot" :class="{ first: idx === 0, last: idx === displayEvents.length - 1 }" />
              <div v-if="idx < displayEvents.length - 1" class="tl-line" />
            </div>
            <div class="tl-body">
              <div class="tl-time">{{ eventTime(ev.timestamp) }}</div>
              <a class="tl-url" :href="ev.page_url" target="_blank" rel="noopener">{{ urlPath(ev.page_url) }}</a>
              <div v-if="ev.referrer && idx === 0" class="tl-ref">from: {{ ev.referrer }}</div>
            </div>
          </div>
          <div v-if="events.length === 0" class="tl-empty">No events found.</div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

interface SessionDetail {
  session_id:   string
  first_seen:   string
  last_seen:    string
  entry_url:    string
  referrer:     string
  source:       string
  medium:       string
  channel:      string
  placement:    string
  campaign_id:  string
  utm_source:   string
  utm_medium:   string
  utm_campaign: string
  page_count:   number
}

interface EventRow {
  timestamp: string
  page_url:  string
  referrer:  string
}

const route   = useRoute()
const router  = useRouter()
const auth    = useAuthStore()

const session = ref<SessionDetail | null>(null)
const events  = ref<EventRow[]>([])
const loading = ref(true)
const error   = ref('')

onMounted(async () => {
  try {
    const { data } = await api.get(`/sessions/${route.params.id}`)
    session.value = data.session
    events.value  = data.events
  } catch (e: unknown) {
    error.value = (e as { response?: { data?: { error?: string } } })?.response?.data?.error || 'Failed to load session'
  } finally {
    loading.value = false
  }
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}

// ── Formatters ──────────────────────────────────────────────────────
function formatTime(ts: string) {
  const d = new Date(ts)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function eventTime(ts: string) {
  return new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function urlPath(url: string) {
  try {
    const u = new URL(url)
    return (u.pathname || '/') + (u.search ? u.search.slice(0, 60) + (u.search.length > 60 ? '…' : '') : '')
  } catch { return url.slice(0, 60) }
}

// Deduplicate A/B redirect pairs: same pathname within 5s → keep the later one
const displayEvents = computed(() => {
  const DEDUP_MS = 5000
  const result: EventRow[] = []
  let prev: { path: string; timeMs: number; idx: number } | null = null

  for (const ev of events.value) {
    let path = '/'
    try { path = new URL(ev.page_url).pathname } catch { path = ev.page_url }
    const timeMs = new Date(ev.timestamp).getTime()

    if (prev && prev.path === path && timeMs - prev.timeMs <= DEDUP_MS) {
      result[prev.idx] = ev          // replace earlier event with later (variant) URL
      prev = { path, timeMs, idx: prev.idx }
    } else {
      prev = { path, timeMs, idx: result.length }
      result.push(ev)
    }
  }
  return result
})

const duration = computed(() => {
  if (!session.value) return '—'
  const ms = new Date(session.value.last_seen).getTime() - new Date(session.value.first_seen).getTime()
  if (ms < 60000) return `${Math.round(ms / 1000)}s`
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
  return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`
})

const CHANNEL_LABELS: Record<string, string> = {
  paid_search: 'Paid Search', paid_shopping: 'Paid Shopping',
  paid_social: 'Paid Social', paid_other: 'Paid Other',
  email: 'Email', sms: 'SMS',
  organic_search: 'Organic Search', organic_shopping: 'Organic Shopping',
  organic_social: 'Organic Social', referral: 'Referral', direct: 'Direct',
}

function channelLabel(ch: string) { return CHANNEL_LABELS[ch] || ch || '—' }

function channelClass(ch: string) {
  if (ch.startsWith('paid'))    return 'badge-paid'
  if (ch === 'email')           return 'badge-email'
  if (ch.startsWith('organic')) return 'badge-organic'
  if (ch === 'direct')          return 'badge-direct'
  return 'badge-other'
}
</script>

<style scoped>
.detail-page { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }

/* Nav (same as dashboard) */
.nav {
  background: var(--nav); padding: 0 1.5rem; height: 52px;
  display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
}
.nav-brand { display: flex; align-items: center; gap: 8px; color: #e2e8f0; font-size: .9rem; font-weight: 600; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
.nav-logout {
  background: transparent; border: 1px solid #334155; color: #94a3b8;
  padding: .35rem .85rem; border-radius: 6px; font-size: .8rem; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.nav-logout:hover { border-color: #94a3b8; color: #e2e8f0; }

/* Sub-header */
.sub-header {
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: .75rem 1.5rem; display: flex; align-items: center; gap: 1.5rem; flex-shrink: 0;
}
.back-btn {
  background: none; border: 1.5px solid var(--border); border-radius: 6px;
  padding: .3rem .8rem; font-size: .8rem; font-weight: 500; color: var(--soft);
  cursor: pointer; transition: border-color .15s, color .15s;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }
.session-title { display: flex; align-items: center; gap: .6rem; }
.session-id-label { font-size: .75rem; color: var(--soft); text-transform: uppercase; letter-spacing: .05em; }
.session-id { font-size: .85rem; color: var(--accent); background: #f0fdfb; padding: .15rem .5rem; border-radius: 4px; }

/* State */
.state-msg { padding: 3rem; text-align: center; color: var(--soft); }
.state-msg.error { color: #ef4444; }

/* Content */
.content { flex: 1; padding: 1.5rem; display: grid; grid-template-columns: 340px 340px 1fr; gap: 1rem; align-items: start; }
@media (max-width: 1100px) { .content { grid-template-columns: 1fr 1fr; } }
@media (max-width: 720px)  { .content { grid-template-columns: 1fr; } }

/* Cards */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.card-title {
  padding: .75rem 1rem; font-size: .75rem; font-weight: 600; color: var(--soft);
  text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border);
  background: #f8fafc;
}
.event-count { font-size: .7rem; color: var(--soft); font-weight: 400; text-transform: none; }

/* Attr grid */
.attr-grid { padding: .25rem 0; }
.attr-row { display: flex; align-items: baseline; gap: .75rem; padding: .5rem 1rem; border-bottom: 1px solid var(--border); }
.attr-row:last-child { border-bottom: none; }
.attr-label { flex-shrink: 0; width: 110px; font-size: .75rem; color: var(--soft); text-transform: uppercase; letter-spacing: .03em; }
.attr-value { font-size: .85rem; color: var(--text); word-break: break-all; }
.attr-value.soft { color: var(--soft); font-style: italic; }
.attr-value.mono { font-family: monospace; font-size: .8rem; }
.attr-link { font-size: .82rem; color: var(--accent); text-decoration: none; word-break: break-all; }
.attr-link:hover { text-decoration: underline; }

/* Badge */
.badge { display: inline-block; padding: .18rem .55rem; border-radius: 4px; font-size: .73rem; font-weight: 600; }
.badge-paid    { background: #eff6ff; color: #2563eb; }
.badge-email   { background: #fdf4ff; color: #9333ea; }
.badge-organic { background: #f0fdf4; color: #16a34a; }
.badge-direct  { background: #f8fafc; color: var(--soft); }
.badge-other   { background: #fff7ed; color: #c2410c; }

/* Journey */
.journey-card { grid-column: 3; }
@media (max-width: 1100px) { .journey-card { grid-column: 1 / -1; } }

.timeline { padding: .75rem 1rem 1rem; }
.timeline-item { display: flex; gap: .75rem; }
.tl-left { display: flex; flex-direction: column; align-items: center; width: 18px; flex-shrink: 0; }
.tl-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 4px;
  background: var(--border); border: 2px solid var(--border);
}
.tl-dot.first { background: var(--accent); border-color: var(--accent); }
.tl-dot.last  { background: #94a3b8; border-color: #94a3b8; }
.tl-line { flex: 1; width: 2px; background: var(--border); margin: 3px 0; min-height: 14px; }
.tl-body { padding-bottom: .85rem; min-width: 0; flex: 1; }
.tl-time { font-size: .72rem; color: var(--soft); margin-bottom: .15rem; }
.tl-url  { font-size: .82rem; color: var(--text); text-decoration: none; word-break: break-all; display: block; }
.tl-url:hover { color: var(--accent); }
.tl-ref  { font-size: .73rem; color: var(--soft); margin-top: .2rem; word-break: break-all; }
.tl-empty { color: var(--soft); font-size: .85rem; padding: .5rem 0; }
</style>
