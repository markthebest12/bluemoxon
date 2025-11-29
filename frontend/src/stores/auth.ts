import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { signIn, signOut, getCurrentUser, fetchAuthSession } from 'aws-amplify/auth'

interface User {
  username: string
  email: string
  role: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => ['admin', 'editor'].includes(user.value?.role || ''))

  async function checkAuth() {
    loading.value = true
    try {
      const currentUser = await getCurrentUser()
      const session = await fetchAuthSession()

      user.value = {
        username: currentUser.username,
        email: currentUser.signInDetails?.loginId || '',
        role: (session.tokens?.idToken?.payload?.['custom:role'] as string) || 'viewer'
      }
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    try {
      await signIn({ username, password })
      await checkAuth()
    } catch (e: any) {
      error.value = e.message || 'Login failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    await signOut()
    user.value = null
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    isEditor,
    checkAuth,
    login,
    logout
  }
})
