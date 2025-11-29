<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const mfaCode = ref('')
const showMfa = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  try {
    await authStore.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e: any) {
    if (e.name === 'UserNotConfirmedException') {
      error.value = 'Please verify your email first'
    } else if (e.name === 'NotAuthorizedException') {
      error.value = 'Invalid email or password'
    } else {
      error.value = e.message || 'Login failed'
    }
  }
}
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center">
    <div class="card w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-moxon-800">BlueMoxon</h1>
        <p class="text-gray-500 mt-2">Sign in to your account</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div v-if="error" class="bg-red-50 text-red-700 p-4 rounded-lg text-sm">
          {{ error }}
        </div>

        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            id="email"
            v-model="email"
            type="email"
            required
            class="input"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            class="input"
            placeholder="••••••••"
          />
        </div>

        <div v-if="showMfa">
          <label for="mfa" class="block text-sm font-medium text-gray-700 mb-1">
            MFA Code
          </label>
          <input
            id="mfa"
            v-model="mfaCode"
            type="text"
            required
            class="input"
            placeholder="123456"
            pattern="[0-9]{6}"
          />
        </div>

        <button
          type="submit"
          class="btn-primary w-full"
          :disabled="authStore.loading"
        >
          {{ authStore.loading ? 'Signing in...' : 'Sign In' }}
        </button>
      </form>

      <p class="text-center text-sm text-gray-500 mt-6">
        Contact administrator for access
      </p>
    </div>
  </div>
</template>
