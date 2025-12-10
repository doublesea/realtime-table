import axios from 'axios'
import { TableData, FilterParams, PaginationParams, ApiResponse, ListResponse, RowPositionResponse, RowDetail, ColumnsConfigResponse } from '../types'

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

  // 添加新数据
  addData: async (data: TableData | TableData[]): Promise<{ success: boolean; added_count: number; columns_updated: boolean; added_columns: string[] }> => {
    try {
      const response = await api.post<ApiResponse<{ success: boolean; added_count: number; columns_updated: boolean; added_columns: string[] }>>('/data/add', {
        data
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

  // 启动自动添加数据
  startAutoAdd: async (batchSize: number = 1, interval: number = 0.5): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await api.post<ApiResponse<{ success: boolean; message: string }>>('/data/auto-add/start', {
        batch_size: batchSize,
        interval: interval
      })
      if (response.data.success) {
        return response.data.data || { success: true, message: response.data.message || '启动成功' }
      } else {
        throw new Error(response.data.message || '启动失败')
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

  // 停止自动添加数据
  stopAutoAdd: async (): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await api.post<ApiResponse<{ success: boolean; message: string }>>('/data/auto-add/stop')
      if (response.data.success) {
        return response.data.data || { success: true, message: response.data.message || '停止成功' }
      } else {
        throw new Error(response.data.message || '停止失败')
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

  // 获取自动添加状态
  getAutoAddStatus: async (): Promise<{ running: boolean }> => {
    try {
      const response = await api.get<ApiResponse<{ running: boolean }>>('/data/auto-add/status')
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
  getFilterOptions: async (): Promise<Record<string, string[]>> => {
    try {
      const response = await api.get<ApiResponse<Record<string, string[]>>>('/data/filters')
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

  // 获取统计信息
  getStatistics: async (): Promise<{ columns: string[]; rows: Record<string, string>[] }> => {
    try {
      const response = await api.get<ApiResponse<{ columns: string[]; rows: Record<string, string>[] }>>('/data/statistics')
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
