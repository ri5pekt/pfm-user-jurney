import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('pfm_token'))

  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password })
    token.value = data.token
    localStorage.setItem('pfm_token', data.token)
  }

  function logout() {
    token.value = null
    localStorage.removeItem('pfm_token')
  }

  return { token, login, logout }
})
