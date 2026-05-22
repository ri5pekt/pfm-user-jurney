<template>
  <div class="dashboard">
    <!-- ── Nav ───────────────────────────────────────────────── -->
    <nav class="nav">
      <div class="nav-brand">
        <span class="dot" />
        PFM Journey Tracker
      </div>
      <button class="nav-logout" @click="handleLogout">Sign out</button>
    </nav>

    <!-- ── Tabs ──────────────────────────────────────────────── -->
    <div class="tabs-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab"
        :class="{ active: active === tab.id }"
        @click="active = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- ── Content ───────────────────────────────────────────── -->
    <main class="content">
      <OverviewTab  v-if="active === 'overview'" />
      <EventsTab    v-else-if="active === 'events'" />
      <SessionsTab  v-else-if="active === 'sessions'" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import OverviewTab  from './tabs/OverviewTab.vue'
import EventsTab    from './tabs/EventsTab.vue'
import SessionsTab  from './tabs/SessionsTab.vue'

const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const tabs = [
  { id: 'overview',  label: 'Overview'  },
  { id: 'events',    label: 'Events'    },
  { id: 'sessions',  label: 'Sessions'  },
]

const active = ref((route.query.tab as string) || 'events')

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Nav */
.nav {
  background: var(--nav);
  padding: 0 1.5rem;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e2e8f0;
  font-size: 0.9rem;
  font-weight: 600;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

.nav-logout {
  background: transparent;
  border: 1px solid #334155;
  color: #94a3b8;
  padding: 0.35rem 0.85rem;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.nav-logout:hover { border-color: #94a3b8; color: #e2e8f0; }

/* Tabs */
.tabs-bar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 1.5rem;
  display: flex;
  gap: 0;
  flex-shrink: 0;
}

.tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.85rem 1.1rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--soft);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
}

.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* Content */
.content {
  flex: 1;
  padding: 1.5rem;
}
</style>
