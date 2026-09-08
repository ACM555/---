import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  getMe,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type AuthUser,
  type LoginPayload,
  type RegisterPayload,
} from '@/api/auth'

interface AuthContextValue {
  user: AuthUser | null
  token: string
  loading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  login: (payload: LoginPayload) => Promise<AuthUser>
  register: (payload: RegisterPayload) => Promise<AuthUser>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)
const TOKEN_KEY = 'outbound_guard_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState(() => window.localStorage.getItem(TOKEN_KEY) ?? '')
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(Boolean(token))

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }

    let mounted = true
    getMe()
      .then((nextUser) => {
        if (mounted) {
          setUser(nextUser)
        }
      })
      .catch(() => {
        window.localStorage.removeItem(TOKEN_KEY)
        if (mounted) {
          setToken('')
          setUser(null)
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
        }
      })

    return () => {
      mounted = false
    }
  }, [token])

  const persistSession = useCallback((nextToken: string, nextUser: AuthUser) => {
    window.localStorage.setItem(TOKEN_KEY, nextToken)
    setToken(nextToken)
    setUser(nextUser)
  }, [])

  const login = useCallback(
    async (payload: LoginPayload) => {
      const result = await loginRequest(payload)
      persistSession(result.token, result.user)
      return result.user
    },
    [persistSession],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      const result = await registerRequest(payload)
      persistSession(result.token, result.user)
      return result.user
    },
    [persistSession],
  )

  const logout = useCallback(async () => {
    if (token) {
      await logoutRequest().catch(() => undefined)
    }
    window.localStorage.removeItem(TOKEN_KEY)
    setToken('')
    setUser(null)
  }, [token])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(user && token),
      isAdmin: user?.role === 'superadmin',
      login,
      register,
      logout,
    }),
    [loading, login, logout, register, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
