<template>
  <div class="widget">
    <div class="widget-header">
      <span class="widget-title">Sessions by Country</span>
      <span class="widget-note">top {{ visible.length }} of {{ props.items.length }}</span>
    </div>

    <div class="bar-list">
      <div class="bar-row" v-for="item in visible" :key="item.country">

        <div class="bar-label">
          <img
            v-if="flagUrl(item.country)"
            :src="flagUrl(item.country)"
            :alt="item.country"
            class="flag"
          />
          <span class="country-name">{{ countryName(item.country) }}</span>
        </div>

        <div class="bar-track">
          <div class="bar-fill" :style="{ width: barWidth(item) + '%' }" />
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
import type { CountryItem } from './types'
import { flagUrl } from '@/composables/useFlags'

const props = defineProps<{
  items: CountryItem[]
  topN?: number
}>()

const topN    = computed(() => props.topN ?? 15)
const visible = computed(() => props.items.slice(0, topN.value))
const maxCount = computed(() => Math.max(...props.items.map(i => i.count), 1))

function barWidth(item: CountryItem): number {
  return (item.count / maxCount.value) * 100
}

const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States', GB: 'United Kingdom', AU: 'Australia', CA: 'Canada',
  DE: 'Germany', FR: 'France', IL: 'Israel', NZ: 'New Zealand',
  ZA: 'South Africa', SG: 'Singapore', AE: 'UAE', NL: 'Netherlands',
  SE: 'Sweden', NO: 'Norway', DK: 'Denmark', CH: 'Switzerland',
  AT: 'Austria', BE: 'Belgium', IT: 'Italy', ES: 'Spain',
  PT: 'Portugal', MX: 'Mexico', BR: 'Brazil', IN: 'India',
  JP: 'Japan', KR: 'South Korea', HK: 'Hong Kong', TW: 'Taiwan',
  PH: 'Philippines', MY: 'Malaysia', TH: 'Thailand', ID: 'Indonesia',
  NG: 'Nigeria', GH: 'Ghana', KE: 'Kenya', EG: 'Egypt',
  SA: 'Saudi Arabia', QA: 'Qatar', KW: 'Kuwait', BH: 'Bahrain',
}

function countryName(code: string): string {
  return COUNTRY_NAMES[code] ?? code
}
</script>

<style scoped>
.bar-list { display: flex; flex-direction: column; gap: 0.5rem; padding: 0.15rem 0; }

.bar-row {
  display: grid;
  grid-template-columns: 160px 1fr 72px;
  align-items: center;
  gap: 0.6rem;
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.flag {
  width: 18px;
  height: 13px;
  object-fit: cover;
  border-radius: 2px;
  flex-shrink: 0;
}

.country-name {
  font-size: 0.78rem;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 8px;
  border-radius: 4px;
  background: rgba(0,0,0,0.06);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 4px;
  background: #06b6d4;
  transition: width 0.5s ease;
}

.bar-stat {
  font-size: 0.75rem;
  color: var(--soft);
  text-align: right;
  white-space: nowrap;
}

.bar-pct {
  font-weight: 700;
  color: var(--text);
  margin-left: 0.25rem;
}
</style>
