import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

interface User {
  username: string
  email: string
  role: string
}

type MfaStep = 'none' | 'totp_required' | 'totp_setup'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const mfaStep = ref<MfaStep>('none')
  const totpSetupUri = ref<string | null>(null)

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isEditor = computed(() => ['admin', 'editor'].includes(user.value?.role || ''))
  const needsMfa = computed(() => mfaStep.value !== 'none')

  async function checkAuth() {
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
      mfaStep.value = 'none'
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string) {
    loading.value = true
    error.value = null
    mfaStep.value = 'none'
    totpSetupUri.value = null

    try {
      const { signIn } = await import('aws-amplify/auth')
      const result = await signIn({ username, password })

      if (result.nextStep.signInStep === 'CONFIRM_SIGN_IN_WITH_TOTP_CODE') {
        mfaStep.value = 'totp_required'
        return // Don't complete login yet, wait for TOTP
      }

      if (result.nextStep.signInStep === 'CONTINUE_SIGN_IN_WITH_TOTP_SETUP') {
        // User needs to set up TOTP
        const { setUpTOTP } = await import('aws-amplify/auth')
        const totpSetup = await setUpTOTP()
        totpSetupUri.value = totpSetup.getSetupUri('BlueMoxon', username).toString()
        mfaStep.value = 'totp_setup'
        return // Wait for user to set up and verify TOTP
      }

      if (result.isSignedIn) {
        await checkAuth()
      }
    } catch (e: any) {
      error.value = e.message || 'Login failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function confirmTotpCode(code: string) {
    loading.value = true
    error.value = null

    try {
      const { confirmSignIn } = await import('aws-amplify/auth')
      const result = await confirmSignIn({ challengeResponse: code })

      if (result.isSignedIn) {
        mfaStep.value = 'none'
        totpSetupUri.value = null
        await checkAuth()
      }
    } catch (e: any) {
      error.value = e.message || 'Invalid code'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function verifyTotpSetup(code: string) {
    loading.value = true
    error.value = null

    try {
      const { verifyTOTPSetup, confirmSignIn } = await import('aws-amplify/auth')
      await verifyTOTPSetup({ code })

      // After TOTP is verified, confirm the sign-in
      const result = await confirmSignIn({ challengeResponse: code })

      if (result.isSignedIn) {
        mfaStep.value = 'none'
        totpSetupUri.value = null
        await checkAuth()
      }
    } catch (e: any) {
      error.value = e.message || 'Invalid code'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    const { signOut } = await import('aws-amplify/auth')
    await signOut()
    user.value = null
    mfaStep.value = 'none'
    totpSetupUri.value = null
  }

  return {
    user,
    loading,
    error,
    mfaStep,
    totpSetupUri,
    isAuthenticated,
    isAdmin,
    isEditor,
    needsMfa,
    checkAuth,
    login,
    confirmTotpCode,
    verifyTotpSetup,
    logout
  }
})
