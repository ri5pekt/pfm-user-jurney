<template>
  <div class="widget">
    <div class="widget-header">
      <span class="widget-title">{{ title }}</span>
      <span class="widget-note">{{ items.length }} total · top {{ visible.length }} shown</span>
    </div>

    <!-- Column headers -->
    <div class="col-headers" v-if="showConversions" :class="{ 'with-revenue': showRevenue }">
      <div class="bar-label" />
      <div class="bar-spacer" />

      <button class="col-h" :class="{ active: sortBy === 'sessions' }" @click="sortBy = 'sessions'">
        Sessions <span class="sort-arrow">{{ sortBy === 'sessions' ? '▼' : '' }}</span>
      </button>

      <button class="col-h c-green" :class="{ active: sortBy === 'orders' }" @click="sortBy = 'orders'">
        Orders <span class="sort-arrow">{{ sortBy === 'orders' ? '▼' : '' }}</span>
      </button>

      <button class="col-h c-green" :class="{ active: sortBy === 'convRate' }" @click="sortBy = 'convRate'">
        CVR <span class="sort-arrow">{{ sortBy === 'convRate' ? '▼' : '' }}</span>
      </button>

      <button v-if="showRevenue" class="col-h c-purple" :class="{ active: sortBy === 'revenue' }" @click="sortBy = 'revenue'">
        Revenue <span class="sort-arrow">{{ sortBy === 'revenue' ? '▼' : '' }}</span>
      </button>
    </div>

    <div class="bar-list">
      <template v-for="item in visible" :key="item.id">
        <!-- Parent row -->
        <div
          class="bar-row"
          :class="{ 'with-conv': showConversions, 'with-revenue': showConversions && showRevenue }"
        >
          <!-- Label with expand toggle -->
          <div class="bar-label">
            <button
              v-if="item.breakdown?.length"
              class="expand-btn"
              :class="{ open: expanded.has(item.id) }"
              @click.stop="toggle(item.id)"
              :title="expanded.has(item.id) ? 'Collapse campaigns' : 'Expand campaigns'"
            >▶</button>
            <span v-else class="expand-placeholder" />
            <span
              class="label-text"
              :class="{ 'label-link': navigable }"
              :title="item.label"
              @click.stop="navigable && goToSessions({ source: item.id })"
            >{{ item.label }}</span>
          </div>

          <!-- Bar track -->
          <div class="bar-track">
            <div class="bar-fill" :class="barColorClass" :style="{ width: barWidth(item) + '%' }" />
          </div>

          <!-- Sessions column -->
          <div class="bar-stat" :class="{ 'col-active': sortBy === 'sessions' }">
            {{ item.count.toLocaleString() }}
            <span class="bar-pct">{{ item.pct }}%</span>
          </div>

          <!-- Orders column -->
          <div class="bar-stat c-green" v-if="showConversions" :class="{ 'col-active': sortBy === 'orders' }">
            {{ (item.orders ?? 0).toLocaleString() }}
          </div>

          <!-- CVR column -->
          <div class="bar-stat c-green" v-if="showConversions" :class="{ 'col-active': sortBy === 'convRate' }">
            <span class="bar-pct c-green-soft">{{ item.convRate ?? 0 }}%</span>
          </div>

          <!-- Revenue column -->
          <div class="bar-stat c-purple" v-if="showConversions && showRevenue" :class="{ 'col-active': sortBy === 'revenue' }">
            {{ fmtUsd(item.revenue ?? 0) }}
          </div>
        </div>

        <!-- Level 2: Channel sub-rows -->
        <template v-if="expanded.has(item.id) && item.breakdown?.length">
          <template v-for="sub in visibleBreakdown(item)" :key="sub.label">
            <!-- Channel row -->
            <div
              class="bar-row sub-row"
              :class="{ 'with-conv': showConversions, 'with-revenue': showConversions && showRevenue }"
            >
              <div class="bar-label sub-label">
                <button
                  v-if="sub.breakdown?.length"
                  class="expand-btn expand-btn-sub"
                  :class="{ open: expandedSub.has(subKey(item.id, sub.label)) }"
                  @click.stop="toggleSub(item.id, sub.label)"
                  :title="expandedSub.has(subKey(item.id, sub.label)) ? 'Collapse campaigns' : 'Expand campaigns'"
                >▶</button>
                <span v-else class="expand-placeholder" />
                <span class="sub-icon">└</span>
                <span
                  class="label-text"
                  :class="{ 'label-link': navigable }"
                  :title="sub.label"
                  @click.stop="navigable && goToSessions({ source: item.id, channel: sub.key ?? sub.label })"
                >{{ sub.label }}</span>
              </div>

              <div class="bar-track sub-track">
                <div class="bar-fill sub-fill" :class="barColorClass" :style="{ width: subBarWidth(sub, item) + '%', opacity: 0.65 }" />
              </div>

              <div class="bar-stat sub-stat" :class="{ 'col-active': sortBy === 'sessions' }">
                {{ sub.count.toLocaleString() }}
                <span class="bar-pct">{{ sub.pct }}%</span>
              </div>
              <div class="bar-stat sub-stat c-green" v-if="showConversions" :class="{ 'col-active': sortBy === 'orders' }">
                {{ sub.orders.toLocaleString() }}
              </div>
              <div class="bar-stat sub-stat c-green" v-if="showConversions" :class="{ 'col-active': sortBy === 'convRate' }">
                <span class="bar-pct c-green-soft" v-if="sub.count">{{ sub.convRate ?? Math.round(sub.orders / sub.count * 1000) / 10 }}%</span>
              </div>
              <div class="bar-stat sub-stat c-purple" v-if="showConversions && showRevenue" :class="{ 'col-active': sortBy === 'revenue' }">
                {{ fmtUsd(sub.revenue) }}
              </div>
            </div>

            <!-- Level 3: Campaign rows under expanded channel -->
            <template v-if="expandedSub.has(subKey(item.id, sub.label)) && sub.breakdown?.length">
              <div
                class="bar-row deep-row"
                :class="{ 'with-conv': showConversions, 'with-revenue': showConversions && showRevenue }"
                v-for="camp in visibleCampaigns(item.id, sub)"
                :key="camp.label"
              >
                <div class="bar-label deep-label">
                  <span class="expand-placeholder" />
                  <span class="sub-icon deep-icon-shift">└</span>
                  <span
                    class="label-text"
                    :class="{ 'label-link': navigable }"
                    :title="camp.label"
                    @click.stop="navigable && goToSessions({ source: item.id, channel: sub.key ?? sub.label, utm_campaign: camp.label })"
                  >{{ camp.label }}</span>
                </div>

                <div class="bar-track sub-track">
                  <div class="bar-fill sub-fill" :class="barColorClass" :style="{ width: (sub.count ? camp.count / sub.count * 100 : 0) + '%', opacity: 0.4 }" />
                </div>

                <div class="bar-stat sub-stat" :class="{ 'col-active': sortBy === 'sessions' }">
                  {{ camp.count.toLocaleString() }}
                  <span class="bar-pct">{{ camp.pct }}%</span>
                </div>
                <div class="bar-stat sub-stat c-green" v-if="showConversions" :class="{ 'col-active': sortBy === 'orders' }">
                  {{ camp.orders.toLocaleString() }}
                </div>
                <div class="bar-stat sub-stat c-green" v-if="showConversions" :class="{ 'col-active': sortBy === 'convRate' }">
                  <span class="bar-pct c-green-soft" v-if="camp.count">{{ Math.round(camp.orders / camp.count * 1000) / 10 }}%</span>
                </div>
                <div class="bar-stat sub-stat c-purple" v-if="showConversions && showRevenue" :class="{ 'col-active': sortBy === 'revenue' }">
                  {{ fmtUsd(camp.revenue) }}
                </div>
              </div>

              <!-- Show all / collapse campaigns within this channel -->
              <div v-if="sub.breakdown.length > BREAKDOWN_DEFAULT" class="show-more-row show-more-deep">
                <button class="show-more-btn" @click="toggleShowAllSub(item.id, sub.label)">
                  <template v-if="showAllSub.has(subKey(item.id, sub.label))">
                    ▲ Show top {{ BREAKDOWN_DEFAULT }}
                  </template>
                  <template v-else>
                    ▼ Show all {{ sub.breakdown.length }} campaigns
                  </template>
                </button>
              </div>
            </template>
          </template>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import type { FunnelItem, BreakdownItem } from './types'

const props = defineProps<{
  title:            string
  items:            FunnelItem[]
  color:            string
  topN?:            number
  showConversions?: boolean
  showRevenue?:     boolean
  navigable?:       boolean   // when true, label clicks link to Sessions with filters applied
}>()

const router = useRouter()

function goToSessions(filters: Record<string, string>) {
  router.push({ path: '/sessions', query: filters })
}

const BREAKDOWN_DEFAULT = 10  // campaigns shown before "show all" button

type SortKey = 'sessions' | 'orders' | 'convRate' | 'revenue'
const sortBy      = ref<SortKey>('sessions')
const expanded    = ref<Set<string>>(new Set())
const expandedSub = ref<Set<string>>(new Set())
const showAllSub  = ref<Set<string>>(new Set())

function toggle(id: string) {
  const s = new Set(expanded.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expanded.value = s
}

function subKey(parentId: string, subLabel: string) {
  return `${parentId}::${subLabel}`
}

function toggleSub(parentId: string, subLabel: string) {
  const key = subKey(parentId, subLabel)
  const s   = new Set(expandedSub.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  expandedSub.value = s
}

function toggleShowAllSub(parentId: string, subLabel: string) {
  const key = subKey(parentId, subLabel)
  const s   = new Set(showAllSub.value)
  if (s.has(key)) s.delete(key)
  else s.add(key)
  showAllSub.value = s
}

// Level 2: channels — show all (typically ≤ 5), just sort
function visibleBreakdown(item: FunnelItem) {
  if (!item.breakdown) return []
  return [...item.breakdown].sort((a, b) => {
    if (sortBy.value === 'orders')   return b.orders  - a.orders
    if (sortBy.value === 'revenue')  return b.revenue - a.revenue
    if (sortBy.value === 'convRate') {
      const ra = a.count ? a.orders / a.count : 0
      const rb = b.count ? b.orders / b.count : 0
      return rb - ra
    }
    return b.count - a.count
  })
}

// Level 3: campaigns within a channel — sorted + capped unless show-all toggled
function visibleCampaigns(parentId: string, sub: BreakdownItem) {
  if (!sub.breakdown) return []
  const sorted = [...sub.breakdown].sort((a, b) => {
    if (sortBy.value === 'orders')   return b.orders  - a.orders
    if (sortBy.value === 'revenue')  return b.revenue - a.revenue
    if (sortBy.value === 'convRate') {
      const ra = a.count ? a.orders / a.count : 0
      const rb = b.count ? b.orders / b.count : 0
      return rb - ra
    }
    return b.count - a.count
  })
  const key = subKey(parentId, sub.label)
  return showAllSub.value.has(key) ? sorted : sorted.slice(0, BREAKDOWN_DEFAULT)
}

const topN = computed(() => props.topN ?? 10)

const sorted = computed(() => {
  const arr = [...props.items]
  if (sortBy.value === 'orders')   return arr.sort((a, b) => (b.orders   ?? 0) - (a.orders   ?? 0))
  if (sortBy.value === 'revenue')  return arr.sort((a, b) => (b.revenue  ?? 0) - (a.revenue  ?? 0))
  if (sortBy.value === 'convRate') return arr.sort((a, b) => (b.convRate ?? 0) - (a.convRate ?? 0))
  return arr.sort((a, b) => b.count - a.count)
})

const visible  = computed(() => sorted.value.slice(0, topN.value))

const maxSessions = computed(() => Math.max(...props.items.map(i => i.count), 1))
const maxOrders   = computed(() => Math.max(...props.items.map(i => i.orders   ?? 0), 1))
const maxRevenue  = computed(() => Math.max(...props.items.map(i => i.revenue  ?? 0), 1))
const maxConvRate = computed(() => Math.max(...props.items.map(i => i.convRate ?? 0), 1))

function barWidth(item: FunnelItem): number {
  if (sortBy.value === 'orders')   return ((item.orders   ?? 0) / maxOrders.value)   * 100
  if (sortBy.value === 'revenue')  return ((item.revenue  ?? 0) / maxRevenue.value)  * 100
  if (sortBy.value === 'convRate') return ((item.convRate ?? 0) / maxConvRate.value) * 100
  return (item.count / maxSessions.value) * 100
}

function subBarWidth(sub: BreakdownItem, parent: FunnelItem): number {
  if (sortBy.value === 'orders')  return parent.orders  ? (sub.orders  / parent.orders)  * 100 : 0
  if (sortBy.value === 'revenue') return parent.revenue ? (sub.revenue / parent.revenue) * 100 : 0
  return (sub.count / parent.count) * 100
}

const barColorClass = computed(() => {
  if (sortBy.value === 'orders' || sortBy.value === 'convRate') return 'bar-fill-green'
  if (sortBy.value === 'revenue') return 'bar-fill-purple'
  return 'bar-fill-blue'
})

function fmtUsd(v: number): string {
  if (v >= 1_000_000) return '$' + (v / 1_000_000).toFixed(1) + 'M'
  if (v >= 1_000)     return '$' + (v / 1_000).toFixed(1) + 'K'
  return '$' + v.toFixed(0)
}
</script>

<style scoped>
.col-headers {
  display: grid;
  grid-template-columns: 210px 1fr 72px 72px 58px;
  gap: 0.6rem;
  padding: 0 0 0.35rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.4rem;
}
.col-headers.with-revenue {
  grid-template-columns: 210px 1fr 72px 72px 58px 72px;
}

.bar-spacer { /* fills the bar column */ }

.col-h {
  font-size: 0.65rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--soft); text-align: right;
  background: none; border: none; cursor: pointer; padding: 0;
  display: flex; align-items: center; justify-content: flex-end; gap: .2rem;
  transition: color .15s;
}
.col-h:hover  { color: var(--text); }
.col-h.active { color: var(--text); }
.col-h.c-green        { color: #6db68a; }
.col-h.c-green.active { color: #15803d; }
.col-h.c-purple        { color: #a78bcc; }
.col-h.c-purple.active { color: #7c3aed; }

.sort-arrow { font-size: .55rem; line-height: 1; opacity: .7; }

/* ── bar list ──────────────────────────────────────────── */
.bar-list { display: flex; flex-direction: column; gap: 0.45rem; padding: 0.2rem 0; }

.bar-row {
  display: grid;
  grid-template-columns: 210px 1fr 72px;
  align-items: center;
  gap: 0.6rem;
}
.bar-row.with-conv    { grid-template-columns: 210px 1fr 72px 72px 58px; }
.bar-row.with-revenue { grid-template-columns: 210px 1fr 72px 72px 58px 72px; }

/* ── label cell ───────────────────────────────────────── */
.bar-label {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.label-text {
  font-size: 0.78rem; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  flex: 1; min-width: 0;
}
.label-link {
  cursor: pointer;
  transition: color .15s;
}
.label-link:hover { color: var(--accent); text-decoration: underline; }

/* ── expand toggle ─────────────────────────────────────── */
.expand-btn {
  flex-shrink: 0;
  width: 16px; height: 16px;
  display: flex; align-items: center; justify-content: center;
  background: none; border: none; cursor: pointer; padding: 0;
  font-size: 0.5rem; color: var(--soft);
  border-radius: 3px;
  transition: color .15s, background .15s, transform .2s ease;
  transform: rotate(0deg);
}
.expand-btn:hover  { color: var(--text); background: rgba(0,0,0,0.06); }
.expand-btn.open   { transform: rotate(90deg); color: var(--text); }

.expand-placeholder {
  flex-shrink: 0;
  width: 16px; height: 16px;
  display: inline-block;
}

/* ── track + fill bars ───────────────────────────────── */
.bar-track {
  height: 8px; border-radius: 4px;
  background: rgba(0,0,0,0.06);
  overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 4px;
  transition: width 0.45s ease, background-color .3s ease;
}
.bar-fill-blue   { background: v-bind(color); }
.bar-fill-green  { background: #22c55e; }
.bar-fill-purple { background: #8b5cf6; }


/* ── stat columns ─────────────────────────────────────── */
.bar-stat {
  font-size: 0.75rem; color: var(--soft);
  text-align: right; white-space: nowrap;
  transition: color .2s;
}
.bar-stat.col-active { color: var(--text); font-weight: 600; }
.bar-pct {
  font-weight: 700; color: var(--text); margin-left: 0.25rem;
}
.c-green      { color: #15803d; }
.c-green-soft { color: #16a34a; }
.c-purple     { color: #7c3aed; }

/* ── sub-rows ─────────────────────────────────────────── */
.sub-row {
  margin-top: -0.1rem;
  margin-bottom: 0.05rem;
}

/* ── show more button ─────────────────────────────────── */
.show-more-row {
  padding-left: 20px;
  margin-top: 0.1rem;
  margin-bottom: 0.2rem;
}
.show-more-deep { padding-left: 52px; }
.show-more-btn {
  background: none; border: none; cursor: pointer; padding: 0;
  font-size: 0.67rem; color: var(--soft);
  transition: color .15s;
}
.show-more-btn:hover { color: var(--text); }

.sub-label {
  padding-left: 2px;
}
.sub-icon {
  flex-shrink: 0;
  width: 16px;
  font-size: 0.65rem;
  color: var(--soft);
  opacity: 0.5;
  text-align: center;
}

/* Level 3 — campaign rows under an expanded channel */
.deep-row { margin-top: -0.1rem; margin-bottom: 0.05rem; }
.deep-label { padding-left: 2px; }
.deep-icon-shift { opacity: 0.35; }
.expand-btn-sub { opacity: 0.8; }

.sub-track {
  height: 5px;
  background: rgba(0,0,0,0.04);
}

.sub-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.sub-stat {
  font-size: 0.7rem;
  color: var(--soft);
}
.sub-stat .bar-pct {
  font-weight: 600;
  color: var(--soft);
  font-size: 0.65rem;
}
</style>
