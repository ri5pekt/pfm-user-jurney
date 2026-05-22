<template>
  <div class="auth-bg">
    <form class="auth-card" @submit.prevent="submit">
      <div class="brand">
        <span class="brand-dot" />
        PFM Journey Tracker
      </div>

      <h2>Sign in</h2>

      <div class="field">
        <label for="email">Email</label>
        <input id="email" v-model="email" type="email" placeholder="you@example.com" autocomplete="email" required />
      </div>

      <div class="field">
        <label for="password">Password</label>
        <input id="password" v-model="password" type="password" placeholder="••••••••" autocomplete="current-password" required />
      </div>

      <p v-if="error" class="err">{{ error }}</p>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth     = useAuthStore()
const router   = useRouter()
const email    = ref('')
const password = ref('')
const error    = ref('')
const loading  = ref(false)

async function submit() {
  error.value   = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/')
  } catch {
    error.value = 'Invalid email or password'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-bg {
  min-height: 100vh;
  background: var(--nav);
  display: flex;
  align-items: center;
  justify-content: center;
}

.auth-card {
  background: var(--surface);
  border-radius: 12px;
  padding: 2.5rem;
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--soft);
  letter-spacing: 0.02em;
}

.brand-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--nav);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--soft);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

input {
  padding: 0.65rem 0.85rem;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 0.95rem;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

input:focus { border-color: var(--accent); }

button {
  margin-top: 0.25rem;
  padding: 0.75rem;
  background: var(--blue);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

button:hover:not(:disabled) { background: var(--blue-dark); }
button:disabled { opacity: 0.6; cursor: not-allowed; }

.err {
  font-size: 0.85rem;
  color: #ef4444;
}
</style>
