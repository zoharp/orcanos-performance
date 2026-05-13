const TOKEN_KEY = 'orcanos_token'
const ROLE_KEY = 'orcanos_role'
const USERNAME_KEY = 'orcanos_username'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const getRole = () => localStorage.getItem(ROLE_KEY)
export const getUsername = () => localStorage.getItem(USERNAME_KEY)
export const isAuthenticated = () => !!getToken()
export const isAdmin = () => getRole() === 'admin'

export function setAuth(token, role, username) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(ROLE_KEY, role)
  localStorage.setItem(USERNAME_KEY, username)
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
  localStorage.removeItem(USERNAME_KEY)
}

export function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken() || ''}`,
  }
}

export async function fetchWithAuth(url, options = {}) {
  const { headers, ...rest } = options
  const res = await fetch(url, {
    ...rest,
    headers: { ...authHeaders(), ...headers },
  })
  if (res.status === 401) {
    clearAuth()
    window.location.href = '/login'
  }
  return res
}
