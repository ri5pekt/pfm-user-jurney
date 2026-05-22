<template>
  <div class="widget">
    <div class="widget-header">
      <span class="widget-title">{{ title }}</span>
      <span class="widget-note">{{ items.length }} total · top {{ visible.length }} shown</span>
    </div>

    <!-- Column headers (only when conversions shown) -->
    <div class="col-headers" v-if="showConversions">
      <div class="bar-label" />
      <div class="bar-spacer" />
      <div class="col-h">Sessions</div>
      <div class="col-h c-green">Orders</div>
    </div>

    <div class="bar-list">
      <div class="bar-row" :class="{ 'with-conv': showConversions }" v-for="item in visible" :key="item.id">

        <!-- Label -->
        <div class="bar-label" :title="item.label">{{ item.label }}</div>

        <!-- Split bar: blue traffic, green conversion portion inside -->
        <div class="bar-track">
          <div class="bar-blue" :style="{ width: trafficWidth(item) + '%' }">
            <div
              v-if="showConversions && item.convRate"
              class="bar-green"
              :style="{ width: item.convRate + '%' }"
            />
          </div>
        </div>

        <!-- Traffic column -->
        <div class="bar-stat">
          {{ item.count.toLocaleString() }}
          <span class="bar-pct">{{ item.pct }}%</span>
        </div>

        <!-- Conversions column -->
        <div class="bar-stat c-green" v-if="showConversions">
          {{ (item.orders ?? 0).toLocaleString() }}
          <span class="bar-pct c-green-soft">{{ item.convRate ?? 0 }}%</span>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FunnelItem } from './types'

const props = defineProps<{
  title:            string
  items:            FunnelItem[]
  color:            string
  topN?:            number
  showConversions?: boolean
}>()

const topN     = computed(() => props.topN ?? 10)
const visible  = computed(() => props.items.slice(0, topN.value))
const maxCount = computed(() => Math.max(...props.items.map(i => i.count), 1))

function trafficWidth(item: FunnelItem) {
  return (item.count / maxCount.value) * 100
}
</script>

<style scoped>
.col-headers {
  display: grid;
  grid-template-columns: 140px 1fr 72px 72px;
  gap: 0.6rem;
  padding: 0 0 0.35rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.4rem;
}
.bar-spacer { /* fills the bar column */ }
.col-h {
  font-size: 0.65rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--soft); text-align: right;
}
.col-h.c-green { color: #16a34a; }

/* ── bar list ──────────────────────────────────────────── */
.bar-list { display: flex; flex-direction: column; gap: 0.55rem; padding: 0.2rem 0; }

.bar-row {
  display: grid;
  grid-template-columns: 140px 1fr 72px;
  align-items: center;
  gap: 0.6rem;
}
.bar-row.with-conv {
  grid-template-columns: 140px 1fr 72px 72px;
}

.bar-label {
  font-size: 0.78rem; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

/* ── track + split bars ───────────────────────────────── */
.bar-track {
  height: 8px; border-radius: 4px;
  background: rgba(0,0,0,0.06);
  overflow: hidden;
}
.bar-blue {
  height: 100%; border-radius: 4px;
  background: v-bind(color);
  transition: width 0.5s ease;
  position: relative;
  overflow: hidden;
}
.bar-green {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  background: #22c55e;
  border-radius: 4px;
  transition: width 0.5s ease;
}

/* ── stat columns ─────────────────────────────────────── */
.bar-stat {
  font-size: 0.75rem; color: var(--soft);
  text-align: right; white-space: nowrap;
}
.bar-pct {
  font-weight: 700; color: var(--text); margin-left: 0.25rem;
}
.c-green      { color: #15803d; }
.c-green-soft { color: #16a34a; }
</style>
