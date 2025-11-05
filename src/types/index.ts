
export interface TableData {
  id: number
  name: string
  email: string
  age: number
  department: string
  salary: number
  status: string
  createTime: string
}

export interface NumberFilter {
  operator?: '=' | '>' | '<' | '>=' | '<='
  value?: number
}

export interface FilterGroup {
  filters: NumberFilter[]
  logic?: 'AND' | 'OR'  // 多个条件之间的逻辑关系
}

export interface FilterParams {
  id?: string | NumberFilter | FilterGroup
  name?: string
  email?: string
  department?: string | string[]  // 支持单选或多选
  status?: string | string[]  // 支持单选或多选
  age?: NumberFilter | FilterGroup
  ageMin?: number
  ageMax?: number
  salary?: NumberFilter | FilterGroup
  salaryMin?: number
  salaryMax?: number
  createTime?: string
}

export interface PaginationParams {
  page: number
  pageSize: number
  sortBy?: string  // 排序字段
  sortOrder?: 'ascending' | 'descending' | null  // 排序方向
}

export interface ApiResponse<T> {
  success: boolean
  data: T
}

export interface ListResponse {
  list: TableData[]
  total: number
  page: number
  pageSize: number
}

export interface FilterOptions {
  departments: string[]
  statuses: string[]
}

export interface RowPositionResponse {
  found: boolean
  position: number  // 在筛选结果中的位置（从0开始）
}
