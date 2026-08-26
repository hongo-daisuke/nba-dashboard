import axios from 'axios'

const toCamelCase = (str: string): string =>
  str.replace(/_([a-z])/g, (_, char: string) => char.toUpperCase())

const toSnakeCase = (str: string): string =>
  str.replace(/([A-Z])/g, (char) => `_${char.toLowerCase()}`)

const deepToCamelCase = (obj: unknown): unknown => {
  if (Array.isArray(obj)) return obj.map(deepToCamelCase)
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, val]) => [
        toCamelCase(key),
        deepToCamelCase(val),
      ]),
    )
  }
  return obj
}

const deepToSnakeCase = (obj: unknown): unknown => {
  if (Array.isArray(obj)) return obj.map(deepToSnakeCase)
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, val]) => [
        toSnakeCase(key),
        deepToSnakeCase(val),
      ]),
    )
  }
  return obj
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  if (config.params) {
    config.params = deepToSnakeCase(config.params)
  }
  return config
})

apiClient.interceptors.response.use((response) => {
  response.data = deepToCamelCase(response.data)
  return response
})

export default apiClient
