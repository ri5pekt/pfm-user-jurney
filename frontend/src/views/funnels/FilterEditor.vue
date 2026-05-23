<template>
  <div class="editor" ref="editorEl">

    <!-- ── Multi-select (country, channel, source) ── -->
    <template v-if="def.type === 'multi_select'">
      <input
        v-model="search"
        class="search-input"
        :placeholder="`Search ${def.label.toLowerCase()}…`"
        ref="searchEl"
      />

      <div class="option-list">
        <label
          v-for="opt in filteredOptions"
          :key="opt.value"
          class="opt-row"
          :class="{ selected: selected.has(opt.value) }"
        >
          <input type="checkbox" :value="opt.value" v-model="checkedValues" />
          <span class="opt-val">
            <span v-if="def.field === 'country'" class="flag">{{ flag(opt.value) }}</span>
            {{ opt.value }}
          </span>
          <span class="opt-count">{{ Number(opt.count).toLocaleString() }}</span>
        </label>

        <div v-if="loading" class="opt-loading">Loading…</div>
        <div v-if="!loading && filteredOptions.length === 0" class="opt-loading">No results</div>
      </div>
    </template>

    <!-- ── String match (entry_url, referrer) ── -->
    <template v-else-if="def.type === 'string'">
      <div class="string-row">
        <select v-model="strOperator" class="op-select">
          <option value="contains">contains</option>
          <option value="equals">equals</option>
          <option value="starts_with">starts with</option>
        </select>
        <input
          v-model="strValue"
          class="str-input"
          placeholder="Enter value…"
          ref="searchEl"
          @keydown.enter="apply"
        />
      </div>
    </template>

    <!-- ── Presence ── -->
    <template v-else-if="def.type === 'presence'">
      <div class="presence-row">
        <label class="pres-opt">
          <input type="radio" v-model="presOp" value="is_set" /> is set
        </label>
        <label class="pres-opt">
          <input type="radio" v-model="presOp" value="is_not_set" /> is not set
        </label>
      </div>
    </template>

    <div class="actions">
      <button class="btn-cancel" @click="$emit('cancel')">Cancel</button>
      <button class="btn-apply" :disabled="!canApply" @click="apply">Apply</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import api from '@/api'
import {
  FILTER_DEFS, buildFilterLabel,
  type FilterField, type FilterOperator, type ActiveFilter
} from './filterTypes'

const props = defineProps<{
  field:    FilterField
  existing?: ActiveFilter | null
}>()

const emit = defineEmits<{
  apply:  [filter: Omit<ActiveFilter, 'id'>]
  cancel: []
}>()

const def       = computed(() => FILTER_DEFS.find(d => d.field === props.field)!)
const search    = ref('')
const searchEl  = ref<HTMLInputElement | null>(null)
const loading   = ref(false)

// Multi-select state
const options       = ref<{ value: string; count: string }[]>([])
const checkedValues = ref<string[]>([])
const selected      = computed(() => new Set(checkedValues.value))

// String state
const strOperator = ref<'contains' | 'equals' | 'starts_with'>('contains')
const strValue    = ref('')

// Presence state
const presOp = ref<'is_set' | 'is_not_set'>('is_set')

// Pre-fill from existing filter
onMounted(async () => {
  searchEl.value?.focus()

  if (props.existing) {
    const f = props.existing
    if (def.value.type === 'multi_select') {
      checkedValues.value = [...f.values]
    } else if (def.value.type === 'string') {
      strOperator.value = f.operator as 'contains' | 'equals' | 'starts_with'
      strValue.value    = f.values[0] ?? ''
    } else {
      presOp.value = f.operator as 'is_set' | 'is_not_set'
    }
  }

  if (def.value.type === 'multi_select') {
    loading.value = true
    try {
      const { data } = await api.get<{ value: string; count: string }[]>(
        `/funnels/filter-values?field=${props.field}`
      )
      options.value = data
    } catch { /* ignore */ } finally {
      loading.value = false
    }
  }
})

const filteredOptions = computed(() => {
  const q = search.value.toLowerCase()
  return q
    ? options.value.filter(o => o.value.toLowerCase().includes(q))
    : options.value
})

const canApply = computed(() => {
  if (def.value.type === 'multi_select') return checkedValues.value.length > 0
  if (def.value.type === 'string')       return strValue.value.trim().length > 0
  return true
})

function apply() {
  if (!canApply.value) return
  let operator: FilterOperator
  let values: string[]

  if (def.value.type === 'multi_select') {
    operator = 'is_any'
    values   = checkedValues.value
  } else if (def.value.type === 'string') {
    operator = strOperator.value
    values   = [strValue.value.trim()]
  } else {
    operator = presOp.value
    values   = []
  }

  emit('apply', {
    field:    props.field,
    operator,
    values,
    label:    buildFilterLabel(props.field, operator, values),
  })
}

// Country emoji flag helper
function flag(iso2: string): string {
  if (!iso2 || iso2.length !== 2) return ''
  return String.fromCodePoint(
    ...iso2.toUpperCase().split('').map(c => 0x1F1E0 + c.charCodeAt(0) - 65)
  )
}
</script>

<style scoped>
.editor {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,.14);
  padding: .6rem;
  min-width: 220px;
  max-width: 280px;
  z-index: 200;
}

.search-input {
  width: 100%; box-sizing: border-box;
  padding: .3rem .55rem; font-size: .78rem;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); outline: none;
  margin-bottom: .35rem;
}
.search-input:focus { border-color: var(--accent); }

.option-list {
  max-height: 180px; overflow-y: auto;
  display: flex; flex-direction: column; gap: .05rem;
  margin-bottom: .4rem;
}

.opt-row {
  display: flex; align-items: center; gap: .45rem;
  padding: .25rem .4rem; border-radius: 5px;
  font-size: .78rem; cursor: pointer;
}
.opt-row:hover, .opt-row.selected { background: rgba(6,182,212,.07); }
.opt-row input[type="checkbox"] { accent-color: var(--accent); flex-shrink: 0; }
.opt-val { flex: 1; display: flex; align-items: center; gap: .3rem; }
.flag { font-size: .9rem; }
.opt-count { color: var(--soft); font-size: .7rem; flex-shrink: 0; }
.opt-loading { font-size: .76rem; color: var(--soft); padding: .3rem .4rem; }

/* String match */
.string-row { display: flex; flex-direction: column; gap: .35rem; margin-bottom: .4rem; }
.op-select {
  padding: .26rem .4rem; font-size: .78rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); cursor: pointer;
}
.str-input {
  width: 100%; box-sizing: border-box;
  padding: .3rem .55rem; font-size: .78rem;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text); outline: none;
}
.str-input:focus { border-color: var(--accent); }

/* Presence */
.presence-row { display: flex; flex-direction: column; gap: .4rem; margin-bottom: .4rem; }
.pres-opt {
  display: flex; align-items: center; gap: .5rem;
  font-size: .8rem; cursor: pointer;
}
.pres-opt input { accent-color: var(--accent); }

/* Actions */
.actions { display: flex; gap: .4rem; justify-content: flex-end; margin-top: .1rem; }
.btn-cancel {
  padding: .26rem .65rem; font-size: .77rem; border-radius: 6px;
  background: none; border: 1px solid var(--border); color: var(--soft); cursor: pointer;
}
.btn-cancel:hover { border-color: var(--text); color: var(--text); }
.btn-apply {
  padding: .26rem .75rem; font-size: .77rem; border-radius: 6px; font-weight: 600;
  background: var(--accent); border: none; color: #fff; cursor: pointer;
}
.btn-apply:disabled { opacity: .4; cursor: not-allowed; }
.btn-apply:not(:disabled):hover { opacity: .88; }
</style>
