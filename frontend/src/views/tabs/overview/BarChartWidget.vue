<template>
  <div class="widget">
    <div class="widget-header">
      <span class="widget-title">{{ title }}</span>
      <span class="widget-note">{{ items.length }} total · top {{ visible.length }} shown</span>
    </div>
    <div class="bar-list">
      <div class="bar-row" v-for="item in visible" :key="item.id">
        <div class="bar-label" :title="item.label">{{ item.label }}</div>
        <div class="bar-track">
          <div
            class="bar-fill"
            :style="{ width: (item.count / maxCount * 100) + '%', background: color }"
          />
        </div>
        <div class="bar-stat">
          {{ item.count.toLocaleString() }}
          <span class="bar-pct">{{ item.pct }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FunnelItem } from './types'

const props = defineProps<{
  title:   string
  items:   FunnelItem[]
  color:   string
  topN?:   number
}>()

const topN    = computed(() => props.topN ?? 10)
const visible = computed(() => props.items.slice(0, topN.value))
const maxCount = computed(() => Math.max(...props.items.map(i => i.count), 1))
</script>

<style scoped>
.bar-list { display: flex; flex-direction: column; gap: 0.55rem; padding: 0.2rem 0; }

.bar-row {
  display: grid;
  grid-template-columns: 140px 1fr 80px;
  align-items: center;
  gap: 0.6rem;
}

.bar-label {
  font-size: 0.78rem; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.bar-track {
  height: 7px; border-radius: 4px;
  background: rgba(255,255,255,0.06);
  overflow: hidden;
}
.bar-fill {
  height: 100%; border-radius: 4px;
  transition: width 0.5s ease;
}

.bar-stat {
  font-size: 0.75rem; color: var(--soft);
  text-align: right; white-space: nowrap;
}
.bar-pct {
  font-weight: 700; color: var(--text);
  margin-left: 0.25rem;
}
</style>
