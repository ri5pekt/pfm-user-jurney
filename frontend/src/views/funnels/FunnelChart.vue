<template>
  <div class="chart-wrap">

    <!-- ── Summary row ──────────────────────────────────── -->
    <div class="summary-row">
      <div class="summary-stat">
        <span class="summary-val">{{ primary.total.toLocaleString() }}</span>
        <span class="summary-label">Started funnel</span>
      </div>

      <div class="summary-stat">
        <div class="conv-pair">
          <span class="summary-val c-green">{{ fmtPct(primary.overall_conversion) }}%</span>
          <span v-if="compare" class="summary-val c-compare">{{ fmtPct(compare.overall_conversion) }}%</span>
        </div>
        <span class="summary-label">Overall conversion</span>
      </div>

      <div class="summary-stat">
        <div class="conv-pair">
          <span class="summary-val c-teal">
            {{ (primary.steps[primary.steps.length - 1]?.count ?? 0).toLocaleString() }}
          </span>
          <span v-if="compare" class="summary-val c-compare">
            {{ (compare.steps[compare.steps.length - 1]?.count ?? 0).toLocaleString() }}
          </span>
        </div>
        <span class="summary-label">Completed funnel</span>
      </div>
    </div>

    <!-- ── Bars ─────────────────────────────────────────── -->
    <div class="bars-area">

      <!-- Track row -->
      <div class="tracks-row">
        <div
          v-for="(step, i) in primary.steps"
          :key="'t' + i"
          class="bar-track-wrap"
        >
          <div class="bar-track">
            <!-- Primary bar -->
            <div
              class="bar-fill bar-primary"
              :class="{ 'bar-half': !!compare }"
              :style="{ height: fmtH(step.pct_total) + '%' }"
            >
              <span class="bar-pct-label">{{ fmtPct(step.pct_total) }}%</span>
            </div>

            <!-- Compare bar (side-by-side) -->
            <div
              v-if="compare"
              class="bar-fill bar-compare"
              :style="{ height: fmtH(compare.steps[i]?.pct_total ?? 0) + '%' }"
            >
              <span class="bar-pct-label">{{ fmtPct(compare.steps[i]?.pct_total ?? 0) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Info row -->
      <div class="info-row">
        <div
          v-for="(step, i) in primary.steps"
          :key="'i' + i"
          class="bar-info"
        >
          <div class="bar-label" :title="step.label">{{ step.label }}</div>

          <!-- Primary stats -->
          <div class="bar-stats">
            <div class="stat-line">
              <span class="dot dot-primary" />
              <span class="stat-count">{{ step.count.toLocaleString() }}</span>
              <span class="stat-pct c-green">({{ fmtPct(step.pct_prev) }}%)</span>
              <span class="stat-desc">{{ i === 0 ? 'Started' : 'Reached' }}</span>
            </div>
            <div class="stat-line" v-if="i > 0 && step.drop_off > 0">
              <span class="dot dot-primary" style="opacity:0" />
              <span class="stat-count c-drop">{{ step.drop_off.toLocaleString() }}</span>
              <span class="stat-pct c-drop">({{ fmtPct(100 - step.pct_prev) }}%)</span>
              <span class="stat-desc">Dropped off</span>
            </div>
          </div>

          <!-- Compare stats -->
          <div class="bar-stats compare-stats" v-if="compare && compare.steps[i]">
            <div class="stat-line">
              <span class="dot dot-compare" />
              <span class="stat-count">{{ compare.steps[i].count.toLocaleString() }}</span>
              <span class="stat-pct c-compare">({{ fmtPct(compare.steps[i].pct_prev) }}%)</span>
              <span class="stat-desc">{{ i === 0 ? 'Started' : 'Reached' }}</span>
            </div>
            <div class="stat-line" v-if="i > 0 && compare.steps[i].drop_off > 0">
              <span class="dot dot-compare" style="opacity:0" />
              <span class="stat-count c-drop">{{ compare.steps[i].drop_off.toLocaleString() }}</span>
              <span class="stat-pct c-drop">({{ fmtPct(100 - compare.steps[i].pct_prev) }}%)</span>
              <span class="stat-desc">Dropped off</span>
            </div>
          </div>

        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
interface StepResult {
  label:     string
  count:     number
  pct_prev:  number
  pct_total: number
  drop_off:  number
}

interface FunnelResult {
  total:              number
  overall_conversion: number
  steps:              StepResult[]
}

const props = defineProps<{
  primary:  FunnelResult
  compare?: FunnelResult
}>()

function fmtH(v: number): number {
  return Math.max(v, 0)      // pct_total 0–100, maps directly to % height
}

function fmtPct(v: number): string {
  if (v >= 10) return v.toFixed(1)
  return v.toFixed(2)
}
</script>

<style scoped>
/* ── Summary ─────────────────────────────────────── */
.summary-row {
  display: flex; gap: 2rem;
  padding: .75rem 1rem;
  background: rgba(6,182,212,.05);
  border: 1px solid rgba(6,182,212,.15);
  border-radius: 10px; margin-bottom: 1.5rem;
}
.summary-stat { display: flex; flex-direction: column; gap: .15rem; }
.summary-val  { font-size: 1.5rem; font-weight: 700; line-height: 1; }
.summary-label { font-size: .68rem; color: var(--soft); text-transform: uppercase; letter-spacing: .04em; }
.c-green   { color: #22c55e; }
.c-teal    { color: var(--accent); }
.c-compare { color: #f43f5e; }
.c-drop    { color: #ef4444; }

.conv-pair { display: flex; align-items: baseline; gap: .6rem; }

/* ── Bars wrapper ────────────────────────────────── */
.bars-area { display: flex; flex-direction: column; overflow-x: auto; }

/* Track row */
.tracks-row {
  display: flex; align-items: flex-end;
  height: 240px;
}

.bar-track-wrap {
  flex: 1; min-width: 120px; max-width: 220px;
  height: 100%;
  padding: 0 .75rem;
  border-right: 1px solid var(--border);
  box-sizing: border-box;
}
.bar-track-wrap:last-child { border-right: none; }

.bar-track {
  width: 100%; height: 100%;
  position: relative;
  background: rgba(0,0,0,.04);
  border-radius: 6px 6px 0 0;
  display: flex;
  align-items: flex-end;    /* bars grow from bottom inside flex */
}

/* Bar fills — side by side when compare present */
.bar-fill {
  position: absolute;
  bottom: 0;
  border-radius: 6px 6px 0 0;
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: .4rem;
  transition: height .6s ease;
  min-height: 22px;
  left: 0; right: 0;   /* full width by default */
}

/* When compare present, split each bar to half width */
.bar-fill.bar-half {
  left: 0; right: 50%;
  border-radius: 6px 0 0 0;
}

.bar-primary { background: #1d4ed8; }
.bar-primary.bar-half { background: #3b82f6; }

.bar-compare {
  position: absolute; bottom: 0;
  left: 50%; right: 0;
  border-radius: 0 6px 0 0;
  display: flex; align-items: flex-start; justify-content: center;
  padding-top: .4rem;
  transition: height .6s ease;
  min-height: 22px;
  background: #f43f5e;
}

.bar-pct-label {
  font-size: .72rem; font-weight: 700; color: #fff;
}

/* ── Info row ─────────────────────────────────────── */
.info-row {
  display: flex;
  border-top: 2px solid var(--border);
}

.bar-info {
  flex: 1; min-width: 120px; max-width: 220px;
  display: flex; flex-direction: column; gap: .5rem;
  padding: .65rem .75rem 1rem;
  border-right: 1px solid var(--border); box-sizing: border-box;
}
.bar-info:last-child { border-right: none; }

.bar-label {
  font-size: .72rem; color: var(--text); text-align: center; line-height: 1.3;
  overflow: hidden; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical; word-break: break-word;
}

.bar-stats {
  display: flex; flex-direction: column; gap: .35rem;
  padding-top: .4rem;
  border-top: 1px solid var(--border);
}

.compare-stats {
  border-top: 1px dashed rgba(244,63,94,.25);
  padding-top: .35rem;
}

.stat-line {
  display: flex; align-items: center; gap: .28rem;
  font-size: .73rem; flex-wrap: wrap; line-height: 1.4;
}

/* Colored dot indicator */
.dot {
  width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
}
.dot-primary { background: #3b82f6; }
.dot-compare { background: #f43f5e; }

.stat-count { font-weight: 600; color: var(--text); }
.stat-pct   { color: var(--soft); }
.stat-desc  { color: var(--soft); }
</style>
