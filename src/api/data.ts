import axios from 'axios'
import { TableData, FilterParams, PaginationParams, ApiResponse, ListResponse, FilterOptions, RowPositionResponse, RowDetail, ColumnsConfigResponse } from '../types'

// 动态获取 API base URL
// 如果是在 NiceGUI 中嵌入，使用相对路径
// 如果是在开发环境，使用 /api
const getApiBaseURL = () => {
  // 检查是否在 NiceGUI 环境中（通过 window.location 判断）
  if (window.location.pathname.includes('/data-table') || window.location.pathname.includes('/static/')) {
    // NiceGUI 环境，使用后端 API 路径
    return '/api'
  }
  // 开发环境
  return '/api'
}

const api = axios.create({
  baseURL: getApiBaseURL(),
  timeout: 30000,
})

export const dataApi = {
  // 获取数据列表
  getList: async (
    params: PaginationParams & { filters?: FilterParams }
  ): Promise<ListResponse> => {
    try {
      const response = await api.post('/data/list', params)
      
      // 调试信息
      console.log('API响应:', response.data)
      
      // 检查响应格式
      const data = response.data
      
      // 如果直接返回了 ListResponse 格式（没有 success 字段）
      if (data.list && data.total !== undefined) {
        return data as ListResponse
      }
      
      // 如果是 ApiResponse 格式
      if (data.success && data.data) {
        return data.data as ListResponse
      }
      
      // 如果都不匹配，抛出错误
      throw new Error('API返回数据格式错误: ' + JSON.stringify(data))
    } catch (error: any) {
      if (error.response) {
        // 服务器返回了错误响应
        console.error('API错误响应:', error.response.data)
        throw new Error(error.response.data?.detail || error.response.data?.message || '服务器错误')
      } else if (error.request) {
        // 请求已发送但没有收到响应
        throw new Error('无法连接到服务器，请确保后端服务已启动')
      } else {
        // 其他错误
        throw error
      }
    }
  },

  // 获取选中行在筛选结果中的位置
  getRowPosition: async (
    rowId: number,
    filters?: FilterParams
  ): Promise<RowPositionResponse> => {
    try {
      const response = await api.post<ApiResponse<RowPositionResponse>>('/data/row-position', {
        rowId,
        filters
      })
      if (response.data.success && response.data.data) {
        return response.data.data
      } else {
        throw new Error('API返回数据格式错误')
      }
    } catch (error: any) {
      if (error.response) {
        throw new Error(error.response.data?.detail || error.response.data?.message || '服务器错误')
      } else if (error.request) {
        throw new Error('无法连接到服务器，请确保后端服务已启动')
      } else {
        throw error
      }
    }
  },

  // 获取筛选选项
  getFilters: async (): Promise<FilterOptions> => {
    try {
      const response = await api.get('/data/filters')
      
      // 调试信息
      console.log('筛选选项API响应:', response.data)
      
      const data = response.data
      
      // 如果直接返回了 FilterOptions 格式
      if (data.departments && data.statuses) {
        return data as FilterOptions
      }
      
      // 如果是 ApiResponse 格式
      if (data.success && data.data) {
        return data.data as FilterOptions
      }
      
      throw new Error('API返回数据格式错误: ' + JSON.stringify(data))
    } catch (error: any) {
      if (error.response) {
        console.error('API错误响应:', error.response.data)
        throw new Error(error.response.data?.detail || error.response.data?.message || '服务器错误')
      } else if (error.request) {
        throw new Error('无法连接到服务器，请确保后端服务已启动')
      } else {
        throw error
      }
    }
  },

  // 获取行详情
  getRowDetail: async (row: TableData): Promise<RowDetail> => {
    try {
      const response = await api.post<ApiResponse<RowDetail>>('/data/row-detail', {
        row
      })
      if (response.data.success && response.data.data) {
        return response.data.data
      } else {
        throw new Error('API返回数据格式错误')
      }
    } catch (error: any) {
      if (error.response) {
        throw new Error(error.response.data?.detail || error.response.data?.message || '服务器错误')
      } else if (error.request) {
        throw new Error('无法连接到服务器，请确保后端服务已启动')
      } else {
        throw error
      }
    }
  },

  // 获取列配置
  getColumnsConfig: async (): Promise<ColumnsConfigResponse> => {
    try {
      const response = await api.get<ApiResponse<ColumnsConfigResponse>>('/data/columns')
      if (response.data.success && response.data.data) {
        return response.data.data
      } else {
        throw new Error('API返回数据格式错误')
      }
    } catch (error: any) {
      if (error.response) {
        throw new Error(error.response.data?.detail || error.response.data?.message || '服务器错误')
      } else if (error.request) {
        throw new Error('无法连接到服务器，请确保后端服务已启动')
      } else {
        throw error
      }
    }
  },
}
