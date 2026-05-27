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
      <router-link
        v-for="tab in tabs"
        :key="tab.id"
        :to="'/' + tab.id"
        class="tab"
        active-class="active"
      >
        {{ tab.label }}
      </router-link>

      <!-- Settings dropdown -->
      <div class="tab-dropdown" :class="{ active: isSettingsActive }" @mouseenter="settingsOpen = true" @mouseleave="settingsOpen = false">
        <span class="tab tab-dd-trigger" :class="{ active: isSettingsActive }">
          Settings <span class="dd-caret">▾</span>
        </span>
        <div v-if="settingsOpen" class="dd-menu">
          <router-link to="/settings/users" class="dd-item" active-class="dd-item-active" @click="settingsOpen = false">
            Users
          </router-link>
        </div>
      </div>
    </div>

    <!-- ── Content ───────────────────────────────────────────── -->
    <main class="content">
      <RouterView v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </RouterView>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineOptions({ name: 'DashboardView' })

const auth   = useAuthStore()
const router = useRouter()
const route  = useRoute()

const tabs = [
  { id: 'overview',  label: 'Overview'  },
  { id: 'events',    label: 'Events'    },
  { id: 'sessions',  label: 'Sessions'  },
  { id: 'funnels',   label: 'Funnels'   },
]

const settingsOpen  = ref(false)
const isSettingsActive = computed(() => route.path.startsWith('/settings'))

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
  align-items: stretch;
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
  text-decoration: none;
  display: flex;
  align-items: center;
}

.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

/* Settings dropdown */
.tab-dropdown {
  position: relative;
  display: flex;
  align-items: stretch;
}

.tab-dd-trigger {
  user-select: none;
  gap: .3rem;
}

.dd-caret { font-size: .65rem; opacity: .6; }

.dd-menu {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 140px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,.08);
  z-index: 100;
  padding: .3rem 0;
  margin-top: 2px;
}

.dd-item {
  display: block;
  padding: .55rem 1rem;
  font-size: .85rem;
  font-weight: 500;
  color: var(--soft);
  text-decoration: none;
  transition: background .1s, color .1s;
}
.dd-item:hover    { background: #f8fafc; color: var(--text); }
.dd-item-active   { color: var(--accent); background: #f0fdfb; }

/* Content */
.content {
  flex: 1;
  padding: 1.5rem;
}
</style>
