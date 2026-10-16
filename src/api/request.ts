import axios from 'axios'
import { message } from 'antd'
import { apiBasePath, deploymentStorageKey } from '@/utils/deploymentPath'

const request = axios.create({
  baseURL: apiBasePath(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config) => {
    const token = window.localStorage.getItem(deploymentStorageKey('outbound_guard_token'))
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

request.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response.data
    }

    const res = response.data

    if (res?.code !== undefined && res.code !== 0) {
      const errorMessage = res.message || '请求失败'
      message.error(errorMessage)
      return Promise.reject(new Error(errorMessage))
    }

    return res
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      const backendMessage = error.response.data?.message || error.response.data?.detail
      const msg =
        backendMessage ||
        (status === 500
          ? '服务器内部错误'
          : status === 404
            ? '接口不存在'
            : status === 409
              ? '数据已存在，请更换后重试'
              : status === 422
                ? '提交信息不符合要求，请检查表单'
            : status === 429
              ? '请求过于频繁，请稍后重试'
              : `网络错误 (${status})`)

      message.error(msg)
      error.message = msg
    } else if (error.code === 'ECONNABORTED') {
      message.error('请求超时，请检查网络后重试')
    } else {
      message.error('网络连接失败，请检查后端服务是否启动')
    }

    return Promise.reject(error)
  },
)

export default request
