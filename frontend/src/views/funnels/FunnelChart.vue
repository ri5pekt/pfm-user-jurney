<template>
  <div class="chart-wrap">

    <!-- Summary row -->
    <div class="summary-row">
      <div class="summary-stat">
        <span class="summary-val">{{ result.total.toLocaleString() }}</span>
        <span class="summary-label">Started funnel</span>
      </div>
      <div class="summary-stat">
        <span class="summary-val c-green">{{ result.overall_conversion }}%</span>
        <span class="summary-label">Overall conversion</span>
      </div>
      <div class="summary-stat">
        <span class="summary-val c-teal">{{ result.steps[result.steps.length - 1]?.count.toLocaleString() ?? 0 }}</span>
        <span class="summary-label">Completed funnel</span>
      </div>
    </div>

    <!-- Bars -->
    <div class="bars-area">
      <div
        v-for="(step, i) in result.steps"
        :key="i"
        class="bar-col"
      >
        <!-- Bar track -->
        <div class="bar-track">
          <div class="bar-bg" />
          <div
            class="bar-fill"
            :class="i === 0 ? 'bar-first' : 'bar-rest'"
            :style="{ height: barHeight(step) + '%' }"
          >
            <span class="bar-pct-label">{{ step.pct_total }}%</span>
          </div>
        </div>

        <!-- Step label -->
        <div class="bar-label" :title="step.label">{{ step.label }}</div>

        <!-- Stats below bar -->
        <div class="bar-stats">
          <div class="stat-line">
            <span class="stat-arrow arrived">→</span>
            <span class="stat-count">{{ step.count.toLocaleString() }}</span>
            <span class="stat-pct arrived">({{ step.pct_prev }}%)</span>
            <span class="stat-desc">{{ i === 0 ? 'Started' : 'Reached' }}</span>
          </div>
          <div class="stat-line" v-if="i > 0 && step.drop_off > 0">
            <span class="stat-arrow dropped">↓</span>
            <span class="stat-count dropped">{{ step.drop_off.toLocaleString() }}</span>
            <span class="stat-pct dropped">({{ (100 - step.pct_prev).toFixed(1) }}%)</span>
            <span class="stat-desc">Dropped off</span>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface StepResult {
  label:       string
  count:       number
  pct_prev:    number
  pct_total:   number
  drop_off:    number
}

interface FunnelResult {
  total:               number
  overall_conversion:  number
  steps:               StepResult[]
}

const props = defineProps<{ result: FunnelResult }>()

function barHeight(step: StepResult): number {
  // height is pct_total of step 1. Step 1 is always 100%.
  return step.pct_total
}
</script>

<style scoped>
/* Summary row */
.summary-row {
  display: flex;
  gap: 2rem;
  padding: .75rem 1rem;
  background: rgba(6,182,212,.05);
  border: 1px solid rgba(6,182,212,.15);
  border-radius: 10px;
  margin-bottom: 1.5rem;
}
.summary-stat { display: flex; flex-direction: column; gap: .15rem; }
.summary-val  { font-size: 1.5rem; font-weight: 700; line-height: 1; }
.summary-label { font-size: .68rem; color: var(--soft); text-transform: uppercase; letter-spacing: .04em; }
.c-green { color: #22c55e; }
.c-teal  { color: var(--accent); }

/* Bars */
.bars-area {
  display: flex;
  align-items: flex-end;
  gap: 0;
  overflow-x: auto;
  padding-bottom: .5rem;
}

.bar-col {
  flex: 1;
  min-width: 120px;
  max-width: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: .6rem;
  padding: 0 .5rem;
  border-right: 1px solid var(--border);
}
.bar-col:last-child { border-right: none; }

/* Bar visualization */
.bar-track {
  width: 100%;
  height: 200px;
  position: relative;
  display: flex;
  align-items: flex-end;
}

.bar-bg {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,.04);
  border-radius: 6px 6px 0 0;
}

.bar-fill {
  position: relative;
  width: 100%;
  border-radius: 6px 6px 0 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: .5rem;
  transition: height .6s ease;
  min-height: 24px;
}
.bar-first { background: #1d4ed8; }
.bar-rest  { background: #3b82f6; }

.bar-pct-label {
  font-size: .78rem;
  font-weight: 700;
  color: #fff;
}

/* Label */
.bar-label {
  font-size: .72rem;
  color: var(--text);
  text-align: center;
  line-height: 1.3;
  max-width: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-word;
}

/* Stats */
.bar-stats {
  display: flex;
  flex-direction: column;
  gap: .25rem;
  width: 100%;
  padding-top: .25rem;
  border-top: 1px solid var(--border);
}
.stat-line {
  display: flex;
  align-items: center;
  gap: .25rem;
  font-size: .72rem;
  flex-wrap: wrap;
}
.stat-arrow  { font-weight: 700; flex-shrink: 0; }
.stat-count  { font-weight: 600; color: var(--text); }
.stat-pct    { color: var(--soft); }
.stat-desc   { color: var(--soft); }

.arrived { color: #22c55e; }
.dropped  { color: #ef4444; }
</style>
