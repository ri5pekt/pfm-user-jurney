<template>
  <div class="overview">
    <div class="placeholder">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
      <h3>Overview</h3>
      <p>Journey graph, funnels, and traffic sources — coming in Phase 2.</p>
    </div>
  </div>
</template>

<style scoped>
.overview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.placeholder {
  text-align: center;
  color: var(--soft);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}

.placeholder svg { opacity: 0.35; }

h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

p {
  font-size: 0.875rem;
  max-width: 280px;
}
</style>
