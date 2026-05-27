<template>
  <div class="users-view">
    <div class="page-header">
      <h2>Users</h2>
      <button class="btn-add" @click="showForm = !showForm">+ Add user</button>
    </div>

    <!-- ── Add user form ───────────────────────────────────── -->
    <div v-if="showForm" class="add-form">
      <h3>New user</h3>
      <div class="form-grid">
        <div class="field">
          <label>Name</label>
          <input v-model="form.name" placeholder="Full name" />
        </div>
        <div class="field">
          <label>Email</label>
          <input v-model="form.email" type="email" placeholder="user@example.com" />
        </div>
        <div class="field">
          <label>Password</label>
          <input v-model="form.password" type="password" placeholder="Min 8 characters" />
        </div>
        <div class="field">
          <label>Role</label>
          <select v-model="form.role">
            <option value="admin">Admin</option>
          </select>
        </div>
      </div>
      <div class="form-actions">
        <span v-if="formError" class="form-error">{{ formError }}</span>
        <button class="btn-cancel" @click="cancelForm">Cancel</button>
        <button class="btn-save" :disabled="saving" @click="createUser">
          {{ saving ? 'Saving…' : 'Save user' }}
        </button>
      </div>
    </div>

    <!-- ── Users table ─────────────────────────────────────── -->
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="state-cell">Loading…</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="5" class="state-cell">No users yet.</td>
          </tr>
          <tr v-for="u in users" :key="u.id" class="row">
            <td class="col-name">{{ u.name || '—' }}</td>
            <td class="col-email">{{ u.email }}</td>
            <td><span class="role-badge">{{ u.role }}</span></td>
            <td class="col-date">{{ formatDate(u.created_at) }}</td>
            <td class="col-action">
              <button
                class="btn-delete"
                :disabled="users.length === 1"
                :title="users.length === 1 ? 'Cannot delete the last user' : 'Remove user'"
                @click="deleteUser(u.id)"
              >Remove</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/api'

interface AdminUser {
  id:         number
  email:      string
  name:       string
  role:       string
  created_at: string
}

const users   = ref<AdminUser[]>([])
const loading = ref(false)
const saving  = ref(false)
const showForm = ref(false)
const formError = ref('')

const form = ref({ name: '', email: '', password: '', role: 'admin' })

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/users')
    users.value = data.users
  } finally {
    loading.value = false
  }
}

async function createUser() {
  formError.value = ''
  if (!form.value.email.trim() || !form.value.password.trim()) {
    formError.value = 'Email and password are required.'
    return
  }
  if (form.value.password.length < 8) {
    formError.value = 'Password must be at least 8 characters.'
    return
  }
  saving.value = true
  try {
    await api.post('/users', form.value)
    form.value = { name: '', email: '', password: '', role: 'admin' }
    showForm.value = false
    await load()
  } catch (err: any) {
    formError.value = err?.response?.data?.error || 'Failed to create user.'
  } finally {
    saving.value = false
  }
}

async function deleteUser(id: number) {
  if (!confirm('Remove this user?')) return
  await api.delete(`/users/${id}`)
  await load()
}

function cancelForm() {
  showForm.value = false
  formError.value = ''
  form.value = { name: '', email: '', password: '', role: 'admin' }
}

function formatDate(ts: string) {
  return new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

onMounted(load)
</script>

<style scoped>
.users-view { display: flex; flex-direction: column; gap: 1.5rem; max-width: 820px; }

.page-header { display: flex; align-items: center; justify-content: space-between; }
.page-header h2 { font-size: 1rem; font-weight: 600; }

.btn-add {
  padding: .4rem .9rem; border-radius: 6px; font-size: .82rem; font-weight: 600;
  background: var(--accent); color: #fff; border: none; cursor: pointer;
  transition: opacity .15s;
}
.btn-add:hover { opacity: .85; }

/* Add form */
.add-form {
  background: var(--surface); border: 1.5px solid var(--accent);
  border-radius: 10px; padding: 1.25rem 1.5rem; display: flex; flex-direction: column; gap: 1rem;
}
.add-form h3 { font-size: .9rem; font-weight: 600; margin: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem 1.25rem; }
.field { display: flex; flex-direction: column; gap: .3rem; }
.field label { font-size: .75rem; font-weight: 600; color: var(--soft); text-transform: uppercase; letter-spacing: .04em; }
.field input, .field select {
  padding: .4rem .65rem; border: 1.5px solid var(--border); border-radius: 6px;
  background: var(--bg); color: var(--text); font-size: .85rem;
}
.field input:focus, .field select:focus { outline: none; border-color: var(--accent); }
.form-actions { display: flex; align-items: center; gap: .75rem; justify-content: flex-end; }
.form-error { color: #ef4444; font-size: .8rem; margin-right: auto; }
.btn-cancel {
  padding: .38rem .8rem; border-radius: 6px; font-size: .82rem;
  background: none; border: 1.5px solid var(--border); color: var(--soft); cursor: pointer;
}
.btn-save {
  padding: .38rem .9rem; border-radius: 6px; font-size: .82rem; font-weight: 600;
  background: var(--accent); color: #fff; border: none; cursor: pointer; transition: opacity .15s;
}
.btn-save:disabled { opacity: .5; cursor: not-allowed; }

/* Table */
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: .85rem; }
thead tr { background: #f8fafc; border-bottom: 1px solid var(--border); }
th { padding: .65rem 1rem; text-align: left; font-size: .75rem; font-weight: 600; color: var(--soft); text-transform: uppercase; letter-spacing: .04em; }
.row { border-bottom: 1px solid var(--border); }
.row:last-child { border-bottom: none; }
td { padding: .7rem 1rem; vertical-align: middle; }
.state-cell { text-align: center; color: var(--soft); padding: 2.5rem; font-size: .875rem; }

.col-name  { font-weight: 500; }
.col-email { color: var(--soft); font-size: .82rem; }
.col-date  { color: var(--soft); font-size: .8rem; white-space: nowrap; }
.col-action { text-align: right; }

.role-badge {
  display: inline-block; padding: .15rem .5rem; border-radius: 4px; font-size: .73rem;
  font-weight: 600; background: #eff6ff; color: #2563eb;
}
.btn-delete {
  padding: .28rem .65rem; border-radius: 5px; font-size: .78rem;
  background: none; border: 1.5px solid #fecaca; color: #ef4444; cursor: pointer;
  transition: background .15s, border-color .15s;
}
.btn-delete:hover:not(:disabled) { background: #fef2f2; border-color: #ef4444; }
.btn-delete:disabled { opacity: .35; cursor: not-allowed; }
</style>
