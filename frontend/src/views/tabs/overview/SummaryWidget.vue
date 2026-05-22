<template>
  <div class="widget">
    <div class="widget-header">
      <span class="widget-title">Overview</span>
      <span class="widget-note">{{ props.rangeLabel }}</span>
    </div>
    <div class="summary-grid">
      <div class="metric">
        <div class="metric-value">{{ props.data.total.toLocaleString() }}</div>
        <div class="metric-label">Sessions</div>
      </div>
      <div class="metric">
        <div class="metric-value" :class="convRate >= 2 ? 'c-green' : 'c-amber'">
          {{ convRate }}%
        </div>
        <div class="metric-label">Conversion Rate</div>
      </div>
      <div class="metric">
        <div class="metric-value c-teal">{{ props.data.thankyou.count.toLocaleString() }}</div>
        <div class="metric-label">Orders</div>
      </div>
      <div class="metric">
        <div class="metric-value">{{ props.data.sources.length }}</div>
        <div class="metric-label">Traffic Sources</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FunnelData } from './types'

const props = defineProps<{ data: FunnelData; rangeLabel: string }>()

const convRate = computed(() =>
  props.data.total ? +(props.data.thankyou.count / props.data.total * 100).toFixed(1) : 0
)
</script>

<style scoped>
.widget { /* shared via global */ }

.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.5rem;
  padding: 0.25rem 0;
}
.metric { display: flex; flex-direction: column; gap: 0.2rem; }
.metric-value {
  font-size: 1.9rem; font-weight: 700; line-height: 1;
  color: var(--text);
}
.metric-label { font-size: 0.72rem; color: var(--soft); text-transform: uppercase; letter-spacing: 0.04em; }
.c-green  { color: #22c55e; }
.c-amber  { color: #f59e0b; }
.c-teal   { color: var(--accent); }
</style>
