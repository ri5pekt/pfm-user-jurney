<template>
  <div class="filter-bar" ref="barEl">

    <!-- Active filter chips -->
    <FilterChip
      v-for="f in filters"
      :key="f.id"
      :label="f.label"
      :variant="variant"
      @edit="startEdit(f)"
      @remove="remove(f.id)"
    />

    <!-- Add filter button -->
    <div class="add-wrap" ref="addWrapEl">
      <button class="btn-add" :class="{ open: menuOpen }" @click.stop="toggleMenu">
        + Add filter
      </button>

      <!-- Filter type menu -->
      <div v-if="menuOpen" class="popover popover-menu" v-click-outside="closeAll">
        <FilterMenu @select="onMenuSelect" @close="closeAll" />
      </div>

      <!-- Filter editor -->
      <div v-if="editorField" class="popover popover-editor" v-click-outside="closeAll">
        <FilterEditor
          :field="editorField"
          :existing="editingFilter"
          @apply="onEditorApply"
          @cancel="closeAll"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FilterChip   from './FilterChip.vue'
import FilterMenu   from './FilterMenu.vue'
import FilterEditor from './FilterEditor.vue'
import {
  type ActiveFilter, type FilterField, nextFilterId,
} from './filterTypes'

const props = defineProps<{
  filters:  ActiveFilter[]
  variant?: 'primary' | 'compare'
}>()

const emit = defineEmits<{ 'update:filters': [filters: ActiveFilter[]] }>()

const menuOpen     = ref(false)
const editorField  = ref<FilterField | null>(null)
const editingFilter = ref<ActiveFilter | null>(null)
const barEl        = ref<HTMLElement | null>(null)

function toggleMenu() {
  if (editorField.value) { closeAll(); return }
  menuOpen.value = !menuOpen.value
}

function onMenuSelect(field: FilterField) {
  menuOpen.value  = false
  editorField.value = field
  editingFilter.value = null
}

function startEdit(f: ActiveFilter) {
  menuOpen.value    = false
  editorField.value = f.field
  editingFilter.value = f
}

function onEditorApply(partial: Omit<ActiveFilter, 'id'>) {
  let next: ActiveFilter[]
  if (editingFilter.value) {
    // replace existing
    next = props.filters.map(f =>
      f.id === editingFilter.value!.id ? { ...partial, id: f.id } : f
    )
  } else {
    next = [...props.filters, { ...partial, id: nextFilterId() }]
  }
  emit('update:filters', next)
  closeAll()
}

function remove(id: number) {
  emit('update:filters', props.filters.filter(f => f.id !== id))
}

function closeAll() {
  menuOpen.value    = false
  editorField.value = null
  editingFilter.value = null
}

// click-outside directive
type ElWithHandler = HTMLElement & { _outsideHandler?: (e: MouseEvent) => void }
const vClickOutside = {
  mounted(el: ElWithHandler, binding: { value: () => void }) {
    el._outsideHandler = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    document.addEventListener('mousedown', el._outsideHandler)
  },
  unmounted(el: ElWithHandler) {
    if (el._outsideHandler) document.removeEventListener('mousedown', el._outsideHandler)
  },
}
</script>

<style scoped>
.filter-bar {
  display: flex; align-items: center; flex-wrap: wrap; gap: .4rem;
  position: relative;
}

.add-wrap { position: relative; }

.btn-add {
  padding: .22rem .65rem; font-size: .76rem; font-weight: 500;
  background: var(--surface); border: 1.5px dashed var(--border);
  border-radius: 20px; color: var(--soft); cursor: pointer;
  transition: border-color .15s, color .15s; white-space: nowrap;
}
.btn-add:hover, .btn-add.open {
  border-color: var(--accent); color: var(--accent); border-style: solid;
}

.popover {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 300;
}
</style>
