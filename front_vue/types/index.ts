
// TableData 现在是动态的，根据后端返回的数据结构确定
// 不再使用固定的字段定义
export type TableData = Record<string, any>

export interface NumberFilter {
  operator?: '=' | '>' | '<' | '>=' | '<='
  value?: number
}

export interface FilterGroup {
  filters: NumberFilter[]
  logic?: 'AND' | 'OR'  // 多个条件之间的逻辑关系
}

// FilterParams 现在是动态的，支持任意字段名
// 不再使用固定的字段定义
export type FilterParams = Record<string, any>

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

export interface RowPositionResponse {
  found: boolean
  position: number  // 在筛选结果中的位置（从0开始）
}

export interface RowDetailItem {
  label: string  // 字段名称
  value: any     // 字段值
  detail?: string  // 详情说明（可选）
}

export type RowDetail = RowDetailItem[]  // 详情数据是一个列表

// 列配置类型
export type ColumnType = 'string' | 'number' | 'date' | 'boolean' | 'bytes'
export type FilterType = 'text' | 'number' | 'select' | 'multi-select' | 'date' | 'none'

export interface ColumnConfig {
  prop: string  // 字段名
  label: string  // 列标题
  type: ColumnType  // 数据类型
  sortable?: boolean  // 是否可排序
  filterable?: boolean  // 是否可筛选
  filterType?: FilterType  // 筛选类型
  minWidth?: number  // 最小宽度
  width?: number  // 固定宽度
  fixed?: 'left' | 'right' | boolean  // 是否固定
  options?: string[]  // 下拉选项（用于select类型）
}

export interface ColumnsConfigResponse {
  columns: ColumnConfig[]
}
