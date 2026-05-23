<template>
  <div class="filter-menu" ref="menuEl">
    <input
      v-model="search"
      class="search-input"
      placeholder="Search filters…"
      ref="searchInput"
      @keydown.esc="$emit('close')"
    />

    <div v-for="group in filteredGroups" :key="group.name" class="group">
      <div class="group-label">{{ group.name }}</div>
      <button
        v-for="def in group.defs"
        :key="def.field"
        class="menu-option"
        @click="$emit('select', def.field)"
      >
        <span class="opt-icon">{{ iconFor(def.field) }}</span>
        {{ def.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { FILTER_DEFS, type FilterField } from './filterTypes'

defineEmits<{ select: [field: FilterField]; close: [] }>()

const search     = ref('')
const menuEl     = ref<HTMLElement | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)

onMounted(() => searchInput.value?.focus())

const groups = computed(() => {
  const map = new Map<string, typeof FILTER_DEFS>()
  for (const def of FILTER_DEFS) {
    if (!map.has(def.group)) map.set(def.group, [])
    map.get(def.group)!.push(def)
  }
  return [...map.entries()].map(([name, defs]) => ({ name, defs }))
})

const filteredGroups = computed(() => {
  const q = search.value.toLowerCase()
  if (!q) return groups.value
  return groups.value
    .map(g => ({ ...g, defs: g.defs.filter(d => d.label.toLowerCase().includes(q)) }))
    .filter(g => g.defs.length > 0)
})

function iconFor(field: FilterField): string {
  const icons: Record<FilterField, string> = {
    country:   '🌍',
    channel:   '📡',
    source:    '🔗',
    entry_url: '🗋',
    referrer:  '↩',
  }
  return icons[field] ?? '⚙'
}
</script>

<style scoped>
.filter-menu {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0,0,0,.14);
  padding: .5rem;
  min-width: 200px;
  max-height: 320px;
  overflow-y: auto;
  z-index: 200;
}

.search-input {
  width: 100%; box-sizing: border-box;
  padding: .32rem .6rem; font-size: .8rem;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 7px; color: var(--text); outline: none;
  margin-bottom: .4rem;
}
.search-input:focus { border-color: var(--accent); }

.group { margin-bottom: .3rem; }
.group-label {
  font-size: .62rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .06em; color: var(--soft); padding: .2rem .4rem;
}

.menu-option {
  display: flex; align-items: center; gap: .5rem; width: 100%;
  padding: .32rem .55rem; border-radius: 6px; border: none;
  background: none; color: var(--text); font-size: .8rem;
  cursor: pointer; text-align: left;
}
.menu-option:hover { background: rgba(6,182,212,.08); color: var(--accent); }
.opt-icon { font-size: .88rem; width: 1.2rem; text-align: center; flex-shrink: 0; }
</style>
