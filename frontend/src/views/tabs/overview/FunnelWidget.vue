<template>
  <div class="widget">
    <div class="widget-header">
      <span class="widget-title">Purchase Funnel</span>
      <span class="widget-note">% of all sessions</span>
    </div>
    <div class="funnel-steps">
      <div class="step" v-for="step in steps" :key="step.label">
        <div class="step-meta">
          <span class="step-label">{{ step.label }}</span>
          <span class="step-stat">
            {{ step.count.toLocaleString() }}
            <span class="step-pct">{{ step.pct }}%</span>
          </span>
        </div>
        <div class="step-track">
          <div class="step-fill" :style="{ width: step.pct + '%', background: step.color }" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FunnelData } from './types'

const props = defineProps<{ data: FunnelData }>()

const steps = computed(() => [
  { label: 'All Sessions',      count: props.data.total,            pct: 100,                               color: '#3b82f6' },
  { label: 'Added to Cart',     count: props.data.cart.count,       pct: props.data.cart.pct,               color: '#f59e0b' },
  { label: 'Reached Checkout',  count: props.data.checkout.count,   pct: props.data.checkout.pct,           color: '#f97316' },
  { label: 'Completed Order',   count: props.data.thankyou.count,   pct: props.data.thankyou.pct,           color: '#22c55e' },
])
</script>

<style scoped>
.funnel-steps { display: flex; flex-direction: column; gap: 0.85rem; padding: 0.25rem 0; }

.step-meta {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 0.28rem;
}
.step-label { font-size: 0.8rem; color: var(--text); }
.step-stat  { font-size: 0.78rem; color: var(--soft); }
.step-pct   { font-weight: 700; color: var(--text); margin-left: 0.3rem; }

.step-track {
  height: 8px; border-radius: 4px;
  background: rgba(255,255,255,0.06);
  overflow: hidden;
}
.step-fill {
  height: 100%; border-radius: 4px;
  transition: width 0.5s ease;
}
</style>
