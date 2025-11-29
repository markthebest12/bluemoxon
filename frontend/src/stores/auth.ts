import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

// Dev mode: bypass Cognito auth when VITE_DEV_AUTH=true
const DEV_AUTH = import.meta.env.VITE_DEV_AUTH === 'true'

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
    // Dev mode: auto-authenticate
    if (DEV_AUTH) {
      user.value = {
        username: 'dev-user',
        email: 'dev@bluemoxon.local',
        role: 'admin'
      }
      return
    }

    loading.value = true
    try {
      const { getCurrentUser, fetchAuthSession } = await import('aws-amplify/auth')
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
    // Dev mode: accept any credentials
    if (DEV_AUTH) {
      user.value = {
        username: username || 'dev-user',
        email: username || 'dev@bluemoxon.local',
        role: 'admin'
      }
      return
    }

    loading.value = true
    error.value = null
    try {
      const { signIn } = await import('aws-amplify/auth')
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
    if (DEV_AUTH) {
      user.value = null
      return
    }

    const { signOut } = await import('aws-amplify/auth')
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
