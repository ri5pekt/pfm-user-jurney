<template>
  <div class="filter-chip" :class="variant">
    <span class="chip-label">{{ label }}</span>
    <button class="chip-edit" @click.stop="$emit('edit')" title="Edit filter">✎</button>
    <button class="chip-remove" @click.stop="$emit('remove')" title="Remove filter">✕</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; variant?: 'primary' | 'compare' }>()
defineEmits<{ edit: []; remove: [] }>()
</script>

<style scoped>
.filter-chip {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .22rem .35rem .22rem .6rem;
  border-radius: 20px; font-size: .76rem; font-weight: 500;
  white-space: nowrap; user-select: none;
  background: rgba(6,182,212,.1);
  border: 1.5px solid rgba(6,182,212,.35);
  color: var(--text);
}
.filter-chip.compare {
  background: rgba(244,63,94,.08);
  border-color: rgba(244,63,94,.35);
}

.chip-label { max-width: 200px; overflow: hidden; text-overflow: ellipsis; }

.chip-edit, .chip-remove {
  background: none; border: none; cursor: pointer; padding: 0 .1rem;
  font-size: .8rem; line-height: 1; color: var(--soft);
  display: flex; align-items: center;
}
.chip-edit:hover  { color: var(--accent); }

.filter-chip.compare .chip-edit:hover { color: #f43f5e; }
.chip-remove:hover { color: #ef4444; }
</style>
