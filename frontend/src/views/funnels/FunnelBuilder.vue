<template>
  <div class="builder">
    <p class="builder-sub">Sessions where users…</p>

    <div class="steps">
      <div
        v-for="(step, i) in steps"
        :key="step.id"
        class="step-wrap"
      >
        <!-- Connector line between steps -->
        <div v-if="i > 0" class="connector" />

        <div class="step-row">
          <span class="step-num">{{ i + 1 }}</span>

          <!-- Configured chip -->
          <div v-if="step.configured" class="step-chip">
            <span class="chip-icon">{{ step.type === 'page_view' ? '🗋' : '⚡' }}</span>
            <span class="chip-label">{{ step.label }}</span>
            <button class="chip-edit" @click="editStep(i)" title="Edit">✎</button>
            <button class="chip-remove" @click="removeStep(i)" title="Remove">✕</button>
          </div>

          <!-- Unconfigured — Add step button -->
          <div v-else class="step-add-wrap">
            <button
              class="btn-add-step"
              :class="{ open: expandedIdx === i && pickerPhase === 'type' }"
              @click="togglePicker(i)"
            >
              + Add step
            </button>
          </div>
        </div>

        <!-- Inline picker panel -->
        <div v-if="expandedIdx === i" class="picker-panel">

          <!-- Phase 1: choose type -->
          <template v-if="pickerPhase === 'type'">
            <div class="picker-section-label">Path</div>
            <button class="picker-option" @click="selectType(i, 'page_view')">
              <span class="opt-icon">🗋</span> Viewed page
            </button>
            <div class="picker-section-label" style="margin-top:.5rem">Custom event</div>
            <button class="picker-option" @click="selectType(i, 'custom_event')">
              <span class="opt-icon">⚡</span> Custom event
            </button>
          </template>

          <!-- Phase 2a: Viewed page config -->
          <template v-else-if="pickerPhase === 'config' && draft.type === 'page_view'">
            <p class="picker-desc">Sessions where users viewed a page.</p>
            <div class="config-row">
              <span class="config-label">where URL</span>
              <select v-model="draft.url_match" class="config-select">
                <option value="contains">contains</option>
                <option value="equals">equals</option>
                <option value="starts_with">starts with</option>
              </select>
            </div>
            <input
              v-model="draft.url_value"
              class="config-input"
              placeholder="e.g. /product, checkout, thank-you"
              @keydown.enter="applyStep(i)"
              ref="configInput"
            />
            <div class="picker-actions">
              <button class="btn-cancel" @click="cancelPicker">Cancel</button>
              <button
                class="btn-apply"
                :disabled="!draft.url_value.trim()"
                @click="applyStep(i)"
              >Apply</button>
            </div>
          </template>

          <!-- Phase 2b: Custom event config -->
          <template v-else-if="pickerPhase === 'config' && draft.type === 'custom_event'">
            <p class="picker-desc">Sessions that fired a custom event.</p>
            <div class="config-row">
              <span class="config-label">event type</span>
            </div>
            <div class="event-suggestions" v-if="eventTypes.length">
              <button
                v-for="et in eventTypes"
                :key="et.event_type"
                class="suggestion"
                :class="{ selected: draft.event_type === et.event_type }"
                @click="draft.event_type = et.event_type"
              >{{ et.event_type }} <span class="sug-count">{{ Number(et.count).toLocaleString() }}</span></button>
            </div>
            <input
              v-model="draft.event_type"
              class="config-input"
              placeholder="or type event name…"
              @keydown.enter="applyStep(i)"
            />
            <div class="picker-actions">
              <button class="btn-cancel" @click="cancelPicker">Cancel</button>
              <button
                class="btn-apply"
                :disabled="!draft.event_type.trim()"
                @click="applyStep(i)"
              >Apply</button>
            </div>
          </template>

        </div>
      </div>
    </div>

    <!-- Add another step -->
    <button
      v-if="steps.length < 8"
      class="btn-add-more"
      @click="addStep"
    >
      + Add step
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import api from '@/api'

export interface BuilderStep {
  id:          number
  type:        'page_view' | 'custom_event' | null
  url_match:   'contains' | 'equals' | 'starts_with'
  url_value:   string
  event_type:  string
  label:       string
  configured:  boolean
}

interface EventTypeRow { event_type: string; count: string }

const emit = defineEmits<{ (e: 'update:steps', steps: BuilderStep[]): void }>()

let nextId = 0
const steps       = ref<BuilderStep[]>([makeStep(), makeStep()])
const expandedIdx = ref<number | null>(null)
const pickerPhase = ref<'type' | 'config'>('type')
const eventTypes  = ref<EventTypeRow[]>([])
const configInput = ref<HTMLInputElement | null>(null)

const draft = reactive<{
  type:       'page_view' | 'custom_event' | null
  url_match:  'contains' | 'equals' | 'starts_with'
  url_value:  string
  event_type: string
}>({ type: null, url_match: 'contains', url_value: '', event_type: '' })

function makeStep(): BuilderStep {
  return { id: nextId++, type: null, url_match: 'contains', url_value: '', event_type: '', label: '', configured: false }
}

function buildLabel(s: BuilderStep): string {
  if (s.type === 'page_view') {
    return `Viewed page ${s.url_match.replace('_', ' ')} "${s.url_value}"`
  }
  if (s.type === 'custom_event') return `Event: ${s.event_type}`
  return ''
}

function togglePicker(i: number) {
  if (expandedIdx.value === i) { cancelPicker(); return }
  expandedIdx.value = i
  pickerPhase.value = 'type'
  draft.type = null; draft.url_value = ''; draft.event_type = ''
}

function editStep(i: number) {
  const s = steps.value[i]
  expandedIdx.value = i
  pickerPhase.value = 'config'
  draft.type       = s.type
  draft.url_match  = s.url_match
  draft.url_value  = s.url_value
  draft.event_type = s.event_type
}

function selectType(i: number, type: 'page_view' | 'custom_event') {
  draft.type       = type
  draft.url_value  = ''
  draft.event_type = ''
  draft.url_match  = 'contains'
  pickerPhase.value = 'config'
  if (type === 'custom_event') loadEventTypes()
  nextTick(() => configInput.value?.focus())
}

function applyStep(i: number) {
  const s = steps.value[i]
  s.type       = draft.type!
  s.url_match  = draft.url_match
  s.url_value  = draft.url_value.trim()
  s.event_type = draft.event_type.trim()
  s.label      = buildLabel(s)
  s.configured = true
  cancelPicker()
  emit('update:steps', steps.value)
}

function removeStep(i: number) {
  if (steps.value.length <= 2) {
    // reset rather than remove when at minimum
    steps.value[i] = makeStep()
  } else {
    steps.value.splice(i, 1)
  }
  cancelPicker()
  emit('update:steps', steps.value)
}

function cancelPicker() {
  expandedIdx.value = null
  pickerPhase.value = 'type'
}

function addStep() {
  steps.value.push(makeStep())
  nextTick(() => { expandedIdx.value = steps.value.length - 1; pickerPhase.value = 'type' })
}

async function loadEventTypes() {
  if (eventTypes.value.length) return
  try {
    const { data } = await api.get<EventTypeRow[]>('/funnels/event-types')
    eventTypes.value = data
  } catch { /* ignore */ }
}

// Expose steps for parent
defineExpose({ steps })
onMounted(() => emit('update:steps', steps.value))
</script>

<style scoped>
.builder { display: flex; flex-direction: column; gap: .5rem; }
.builder-sub { font-size: .8rem; font-weight: 600; color: var(--soft); margin: 0 0 .25rem; text-transform: uppercase; letter-spacing: .05em; }

/* Steps */
.steps { display: flex; flex-direction: column; gap: 0; }
.step-wrap { display: flex; flex-direction: column; }
.connector { width: 2px; height: 14px; background: var(--border); margin-left: 1.15rem; }

.step-row { display: flex; align-items: flex-start; gap: .65rem; }
.step-num {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--accent); color: #fff;
  font-size: .72rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: .1rem;
}

/* Add step button */
.step-add-wrap { flex: 1; }
.btn-add-step {
  padding: .35rem .85rem; font-size: .82rem; font-weight: 500;
  background: var(--surface); border: 1.5px dashed var(--border);
  border-radius: 8px; color: var(--soft); cursor: pointer;
  transition: border-color .15s, color .15s;
}
.btn-add-step:hover, .btn-add-step.open { border-color: var(--accent); color: var(--accent); }

/* Configured chip */
.step-chip {
  flex: 1; display: flex; align-items: center; gap: .45rem;
  padding: .4rem .75rem; border-radius: 8px;
  background: rgba(6,182,212,.08); border: 1.5px solid rgba(6,182,212,.3);
  font-size: .82rem;
}
.chip-icon { font-size: .9rem; flex-shrink: 0; }
.chip-label { flex: 1; color: var(--text); font-weight: 500; }
.chip-edit, .chip-remove {
  background: none; border: none; cursor: pointer;
  font-size: .85rem; color: var(--soft); padding: 0 .1rem;
  line-height: 1;
}
.chip-edit:hover  { color: var(--accent); }
.chip-remove:hover { color: #ef4444; }

/* Picker panel */
.picker-panel {
  margin: .35rem 0 .35rem 2.35rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: .75rem 1rem;
  box-shadow: 0 4px 16px rgba(0,0,0,.12);
  max-width: 340px;
}

.picker-section-label {
  font-size: .65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: var(--soft); margin-bottom: .3rem;
}

.picker-option {
  display: flex; align-items: center; gap: .5rem; width: 100%;
  padding: .45rem .6rem; border-radius: 7px; border: none;
  background: none; color: var(--text); font-size: .83rem;
  cursor: pointer; text-align: left;
}
.picker-option:hover { background: rgba(6,182,212,.08); color: var(--accent); }
.opt-icon { font-size: .95rem; width: 1.2rem; text-align: center; }

/* Config form */
.picker-desc { font-size: .78rem; color: var(--soft); margin: 0 0 .6rem; }
.config-row { display: flex; align-items: center; gap: .5rem; margin-bottom: .45rem; }
.config-label { font-size: .78rem; color: var(--soft); white-space: nowrap; }
.config-select {
  padding: .25rem .4rem; font-size: .78rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); cursor: pointer;
}
.config-input {
  width: 100%; box-sizing: border-box;
  padding: .38rem .6rem; font-size: .82rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 7px; color: var(--text);
  outline: none;
}
.config-input:focus { border-color: var(--accent); }

/* Event type suggestions */
.event-suggestions { display: flex; flex-wrap: wrap; gap: .35rem; margin-bottom: .45rem; }
.suggestion {
  padding: .25rem .6rem; border-radius: 20px; font-size: .75rem;
  background: var(--bg); border: 1px solid var(--border);
  color: var(--text); cursor: pointer; display: flex; align-items: center; gap: .35rem;
}
.suggestion:hover, .suggestion.selected { border-color: var(--accent); background: rgba(6,182,212,.08); color: var(--accent); }
.sug-count { color: var(--soft); font-size: .7rem; }

/* Picker actions */
.picker-actions { display: flex; gap: .5rem; justify-content: flex-end; margin-top: .6rem; }
.btn-cancel {
  padding: .3rem .7rem; font-size: .8rem; border-radius: 6px;
  background: none; border: 1px solid var(--border); color: var(--soft); cursor: pointer;
}
.btn-cancel:hover { border-color: var(--text); color: var(--text); }
.btn-apply {
  padding: .3rem .85rem; font-size: .8rem; border-radius: 6px; font-weight: 600;
  background: var(--accent); border: none; color: #fff; cursor: pointer;
}
.btn-apply:disabled { opacity: .4; cursor: not-allowed; }
.btn-apply:not(:disabled):hover { opacity: .88; }

/* Add more steps */
.btn-add-more {
  align-self: flex-start; margin-top: .35rem;
  padding: .32rem .85rem; font-size: .8rem; font-weight: 500;
  background: none; border: 1px solid var(--border);
  border-radius: 7px; color: var(--soft); cursor: pointer;
}
.btn-add-more:hover { border-color: var(--accent); color: var(--accent); }
</style>
