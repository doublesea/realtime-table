<template>
  <el-card class="table-card" :body-style="{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }">
    <!-- 工具栏 -->
    <div class="toolbar" style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
      <!-- Left: Pagination -->
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[100, 200, 500, 1000, 2000]"
          :total="pagination.total"
          :pager-count="5"
          layout="total, sizes, prev, pager, next, jumper"
          background
          small
          :prev-icon="ArrowLeft"
          :next-icon="ArrowRight"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
      <!-- Right: Statistics, VXE Native Custom, Reset -->
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button :icon="DataAnalysis" size="small" @click="handleShowStatistics">
          统计
        </el-button>
        <el-button :icon="Setting" size="small" @click="handleOpenColumnSettings">
          列设置
        </el-button>
        <el-button :icon="Refresh" size="small" @click="handleReset">重置所有筛选</el-button>
      </div>
    </div>

    <!-- 数据表格容器 -->
    <div class="table-container">
      <!-- 轻量级加载指示器（顶部进度条） -->
      <div v-if="silentLoading" class="silent-loading-bar"></div>
      <vxe-table
        ref="tableRef"
        :id="vxeTableId"
        :key="vxeTableKey"
        :data="tableData"
        :loading="loading && !silentLoading"
        stripe
        border
        size="mini"
        height="100%"
        show-overflow="ellipsis"
        show-header-overflow="ellipsis"
        :row-config="{ isHover: true, isCurrent: true, keyField: 'id' }"
        :column-config="{ resizable: true }"
        :custom-config="{ storage: true, immediate: true }"
        :toolbar-config="{ custom: true }"
        :scroll-y="{ enabled: true, gt: 0 }"
        :filter-config="{ remote: true }"
        :sort-config="{ remote: true, showIcon: true }"
        @sort-change="handleVxeSortChange"
        @filter-change="handleVxeFilterChange"
        @cell-click="handleVxeCellClick"
        @toggle-row-expand="handleVxeExpandChange"
      >
        <!-- 展开列 -->
        <vxe-column type="expand" width="50" fixed="left">
          <template #content="{ row }">
            <div class="expand-detail" v-loading="rowDetailsLoading[row.id]">
              <template v-if="rowDetails[row.id] && rowDetails[row.id].length > 0">
                <vxe-table 
                  :data="rowDetails[row.id]" 
                  border 
                  size="mini" 
                  style="width: fit-content; max-width: 100%"
                  show-overflow="ellipsis"
                  show-header-overflow="ellipsis"
                >
                  <vxe-column 
                    v-for="column in getDetailColumns(rowDetails[row.id])" 
                    :key="column.prop"
                    :field="column.prop" 
                    :title="column.label" 
                    :min-width="column.minWidth || 100"
                  >
                    <template #default="{ row: detailRow }">
                      <span :class="column.class">{{ detailRow[column.prop] ?? '-' }}</span>
                    </template>
                  </vxe-column>
                </vxe-table>
              </template>
              <div v-else-if="rowDetailsError[row.id]" class="error-message">
                {{ rowDetailsError[row.id] }}
              </div>
              <div v-else class="loading-message">
                正在加载详情...
              </div>
            </div>
          </template>
          <template #header>
            <span style="font-size: 14px; font-weight: 600;">+</span>
          </template>
        </vxe-column>

        <!-- 动态生成列 -->
        <template v-for="col in columnConfig" :key="col.prop">
          <vxe-column
            :field="col.prop"
            :title="col.label"
            :min-width="col.minWidth || 120"
            :width="getColumnWidth(col) || undefined"
            :fixed="(col.fixed as any)"
            :sortable="col.sortable"
            :visible="col.prop !== 'id'"
            :filters="col.filterable && col.filterType !== 'none' ? getInitialFilterData(col) : []"
            :filter-render="{}"
          >
            <!-- 使用 vxe-table 原生筛选插槽 -->
            <template #filter="{ column, $panel }">
              <div v-if="ensureFilterData(column.filters[0], col)" class="vxe-filter-custom-panel">
                <div class="filter-header">{{ col.label }}筛选</div>
                
                <div class="filter-body">
                  <!-- 文本筛选 -->
                  <template v-if="col.filterType === 'text'">
                    <el-input
                      v-model="column.filters[0].data"
                      :placeholder="`输入关键词`"
                      size="small"
                      clearable
                      @input="$panel.changeOption($event, !!column.filters[0].data, column.filters[0])"
                      @keyup.enter="$panel.confirmFilter()"
                    />
                  </template>
                  
                  <!-- 数字筛选 -->
                  <template v-else-if="col.filterType === 'number'">
                    <div class="filter-number-wrapper" @mousedown.stop @mouseup.stop @click.stop>
                      <div v-for="(item, index) in column.filters[0].data.filters" :key="index" class="number-filter-item">
                        <el-select 
                          v-model="item.operator" 
                          placeholder="OP" 
                          size="small" 
                          style="width: 70px" 
                          :teleported="false"
                          @change="$panel.changeOption($event, true, column.filters[0])"
                        >
                          <el-option label="=" value="=" />
                          <el-option label=">" value=">" />
                          <el-option label="<" value="<" />
                          <el-option label=">=" value=">=" />
                          <el-option label="<=" value="<=" />
                        </el-select>
                        <el-input
                          v-model="item.value"
                          placeholder="值"
                          size="small"
                          style="flex: 1"
                          @input="$panel.changeOption($event, true, column.filters[0])"
                          @keyup.enter="$panel.confirmFilter()"
                        />
                        <el-button v-if="column.filters[0].data.filters.length > 1" :icon="Delete" size="small" text type="danger" @click.stop="column.filters[0].data.filters.splice(index, 1); $panel.changeOption($event, true, column.filters[0])" />
                      </div>
                      <el-button size="small" text type="primary" @click.stop="column.filters[0].data.filters.push({ operator: '=', value: '' })">+ 添加条件</el-button>
                      <div class="logic-switch" v-if="column.filters[0].data.filters.length > 1">
                        <el-radio-group v-model="column.filters[0].data.logic" size="small" @change="$panel.changeOption($event, true, column.filters[0])">
                          <el-radio-button label="AND">AND</el-radio-button>
                          <el-radio-button label="OR">OR</el-radio-button>
                        </el-radio-group>
                      </div>
                    </div>
                  </template>
                  
                  <!-- 下拉筛选 -->
                  <template v-else-if="col.filterType === 'multi-select' || col.filterType === 'select'">
                    <el-select
                      v-model="column.filters[0].data"
                      :placeholder="`请选择`"
                      size="small"
                      clearable
                      :multiple="col.filterType === 'multi-select'"
                      collapse-tags
                      style="width: 100%"
                      :teleported="false"
                      @change="$panel.changeOption($event, Array.isArray(column.filters[0].data) ? column.filters[0].data.length > 0 : !!column.filters[0].data, column.filters[0])"
                      @mousedown.stop
                      @mouseup.stop
                      @click.stop
                    >
                      <el-option
                        v-for="option in getFilterOptions(col.prop)"
                        :key="option"
                        :label="option"
                        :value="option"
                      />
                    </el-select>
                  </template>

                  <!-- 日期筛选 -->
                  <template v-else-if="col.filterType === 'date'">
                    <el-input
                      v-model="column.filters[0].data"
                      placeholder="YYYY-MM-DD"
                      size="small"
                      clearable
                      @input="$panel.changeOption($event, !!column.filters[0].data, column.filters[0])"
                      @keyup.enter="$panel.confirmFilter()"
                    />
                  </template>
                </div>
              </div>
            </template>

            <template #default="{ row }">
              <template v-if="col.filterType === 'multi-select' || col.filterType === 'select'">
                <span class="list-column-tag">
                  {{ row[col.prop] ?? '-' }}
                </span>
              </template>
              <template v-else-if="col.type === 'bytes'">
                <span class="bytes-display" :title="row[col.prop]">
                  {{ row[col.prop] ?? '-' }}
                </span>
              </template>
              <template v-else>
                {{ row[col.prop] ?? '-' }}
              </template>
            </template>
          </vxe-column>
        </template>
      </vxe-table>
    </div>

    <!-- 统计信息弹窗 -->
    <el-dialog
      v-model="showStatisticsDialog"
      title="数据统计"
      width="600px"
      :close-on-click-modal="true"
    >
      <div class="statistics-content" v-loading="statisticsLoading">
        <vxe-table 
          v-if="statisticsData.rows.length > 0" 
          :data="statisticsData.rows" 
          border 
          stripe 
          size="small"
          style="width: 100%"
        >
          <vxe-column
            v-for="col in statisticsData.columns"
            :key="col"
            :field="col"
            :title="col"
            :min-width="col === '描述' ? 200 : 120"
          />
        </vxe-table>
        <el-empty v-else-if="!statisticsLoading" description="暂无统计数据" />
      </div>
      <template #footer>
        <el-button @click="showStatisticsDialog = false">关闭</el-button>
        <el-button type="primary" @click="loadStatistics" :loading="statisticsLoading">刷新</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Delete, Setting, ArrowLeft, ArrowRight, DataAnalysis } from '@element-plus/icons-vue'
import { TableData, FilterParams, RowDetail, ColumnConfig } from '../types'
import type { VxeTableInstance, VxeTableEvents } from 'vxe-table'
import axios from 'axios'

// Props definition
const props = defineProps<{
  apiUrl: string
  tableId?: string
}>()

// 获取 tableId
const getTableId = (): string | null => {
  if (props.tableId) return props.tableId
  const root = document.getElementById('root')
  return root?.dataset.tableId || null
}

// Define API client with automatic x-table-id header injection
const createApi = (baseUrl: string) => {
  const client = axios.create({
    baseURL: baseUrl || '',
    timeout: 30000
  })
  
  // 添加请求拦截器，自动注入 x-table-id header
  client.interceptors.request.use((config) => {
    const tableId = getTableId()
    if (tableId && config.headers) {
      config.headers['x-table-id'] = tableId
    }
    return config
  })
  
  return {
    getList: async (params: any) => {
      const response = await client.post('/list', params)
      const data = response.data
      if (data.success && data.data) {
        return data.data
      }
      return data
    },
    getColumnsConfig: async () => {
      const response = await client.get('/columns')
      const data = response.data
      if (data.success && data.data) {
        return data.data
      }
      return data
    },
    getRowDetail: async (row: any) => {
      const response = await client.post('/row-detail', { row })
      const data = response.data
      if (data.success && data.data) {
        return data.data
      }
      return data
    },
    getRowPosition: async (row_id: any, filters?: any, sortBy?: string, sortOrder?: string) => {
      const response = await client.post('/row-position', { row_id, filters, sortBy, sortOrder })
      const data = response.data
      if (data.success && data.data) {
        return data.data
      }
      return data
    },
    getFilterOptions: async () => {
      const response = await client.get('/filters')
      const data = response.data
      if (data.success && data.data) {
        return data.data
      }
      return data
    },
    getStatistics: async () => {
      const response = await client.get('/statistics')
      const data = response.data
      if (data.success && data.data) {
        return data.data
      }
      return data
    }
  }
}

const dataApi = createApi(props.apiUrl)

// 响应式数据
const tableData = ref<TableData[]>([])
const loading = ref(false)
const silentLoading = ref(false)
const selectedRowId = ref<number | null>(null)
const tableRef = ref<VxeTableInstance<TableData>>()
const filterOptions = reactive<Record<string, string[]>>({})

// 动态表格 ID，在 mount 时固定，避免 computed 导致的潜在循环
const vxeTableId = ref('vxe_data_table')

// 表格 Key，仅在列的 prop 列表真正改变时才变化
const vxeTableKey = ref('vxe_key_initial')

// 使用普通对象缓存初始化的筛选数据数组，确保引用恒定
const initialFilterDataMap: Record<string, any[]> = {}

const getInitialFilterData = (col: ColumnConfig) => {
  if (initialFilterDataMap[col.prop]) {
    return initialFilterDataMap[col.prop]
  }
  return []
}

// 行详情数据
const rowDetails = reactive<Record<number, RowDetail>>({})
const rowDetailsLoading = reactive<Record<number, boolean>>({})
const rowDetailsError = reactive<Record<number, string>>({})

// 列配置
const columnConfig = ref<ColumnConfig[]>([])
const columnWidths = reactive<Record<string, number>>({})

// 统计信息
const showStatisticsDialog = ref(false)
const statisticsLoading = ref(false)
const statisticsData = ref<{ columns: string[]; rows: Record<string, string>[] }>({ columns: [], rows: [] })

const pagination = reactive({
  page: 1,
  pageSize: 200,
  total: 0
})

const sortInfo = reactive({
  prop: 'id' as string | undefined,
  order: 'ascending' as 'ascending' | 'descending' | null | undefined
})

const loadColumnsConfig = async () => {
  try {
    const config = await dataApi.getColumnsConfig()
    
    // 1. 预先初始化所有列的筛选数据数组（引用级别固定）
    config.columns.forEach((col: any) => {
      if (!initialFilterDataMap[col.prop]) {
        let data: any = ''
        if (col.filterType === 'number') {
          data = { filters: [{ operator: '=', value: '' }], logic: 'AND' }
        } else if (col.filterType === 'multi-select') {
          data = []
        }
        initialFilterDataMap[col.prop] = [{ data }]
      }
    })

    // 2. 检查列结构是否真正发生变化
    const oldProps = columnConfig.value.map(c => c.prop).join(',')
    const newProps = config.columns.map((c: any) => c.prop).join(',')
    
    if (oldProps !== newProps || columnConfig.value.length === 0) {
      columnConfig.value = config.columns
      // 仅在结构变化时更新 Key，触发 VXE 彻底重绘
      vxeTableKey.value = `vxe_key_${Date.now()}_${newProps.length}`
    }
    
    await refreshFilterOptions(true)
  } catch (error) {
    ElMessage.error('加载列配置失败')
  }
}

const loadData = async (keepSelectedRow = false, silent = false) => {
  if (silent) silentLoading.value = true
  else loading.value = true
  try {
    const previousPage = pagination.page
    const previousTotal = pagination.total
    const filters: FilterParams = {}
    
    // 直接从 vxe-table 实例或 initialFilterDataMap 读取筛选状态，确保数据源统一
    // 这样 handleVxeFilterChange 只需要触发 loadData，而不需要维护 filterForm
    columnConfig.value.forEach(col => {
      if (!col.filterable) return
      const prop = col.prop
      
      // 获取当前列的筛选器状态
      // 优先从 VXE 实例获取最新的（如果已经挂载），否则从初始化缓存获取
      let option = null
      if (tableRef.value) {
        const column = tableRef.value.getColumnByField(prop)
        if (column && column.filters && column.filters.length > 0) {
          option = column.filters[0]
        }
      }
      
      // 如果 table 未准备好，从备份 Map 获取
      if (!option && initialFilterDataMap[prop]) {
        option = initialFilterDataMap[prop][0]
      }

      if (option && option.checked && option.data !== undefined) {
        const data = option.data
        if (col.filterType === 'number') {
          if (data && typeof data === 'object' && Array.isArray(data.filters)) {
            const validFilters = data.filters.filter((f: any) => f.operator && f.value !== '')
            if (validFilters.length > 0) {
              if (validFilters.length === 1) filters[prop] = validFilters[0]
              else filters[prop] = { filters: validFilters, logic: data.logic || 'AND' }
            }
          }
        } else if (col.filterType === 'multi-select' || col.filterType === 'select') {
          if (Array.isArray(data)) {
            if (data.length > 0) filters[prop] = data
          } else if (data !== '' && data !== null) {
            filters[prop] = data
          }
        } else if (data !== '' && data !== null) {
          filters[prop] = data
        }
      }
    })

    const requestFilters = Object.keys(filters).length > 0 ? filters : undefined
    
    // 调试：打印发送给后端的筛选参数
    if (requestFilters) {
      console.log('Sending filters to backend:', JSON.stringify(requestFilters, null, 2))
    }
    
    // 如果没有指定排序，默认按ID升序（最新的在后）
    const sortBy = sortInfo.prop || 'id'
    const sortOrder = sortInfo.order || 'ascending'

    let targetPage = pagination.page
    let shouldKeepSelected = true
    if (keepSelectedRow && selectedRowId.value !== null) {
      try {
        const positionResponse = await dataApi.getRowPosition(selectedRowId.value, requestFilters, sortBy, sortOrder)
        if (positionResponse.found) {
          targetPage = Math.floor(positionResponse.position / pagination.pageSize) + 1
        } else {
          selectedRowId.value = null
          shouldKeepSelected = false
        }
      } catch (error) {}
    }

    const requestParams = {
      page: targetPage,
      pageSize: pagination.pageSize,
      filters: requestFilters,
      sortBy: sortBy,
      sortOrder: sortOrder
    }
    
    const response = await dataApi.getList(requestParams)
    console.log(`Received ${response.list.length} rows from backend (total: ${response.total})`)
    tableData.value = response.list
    pagination.total = response.total
    pagination.page = response.page
    pagination.pageSize = response.pageSize
    
    // Clear selection if not found in current data
    if (selectedRowId.value !== null && !shouldKeepSelected) {
      if (tableRef.value) {
        tableRef.value.clearCurrentRow()
      }
    }

    await nextTick()
    
    // 如果是静默刷新（自动刷新），检查是否需要自动跳转到最新数据
    if (silent) {
      const previousLastPage = previousTotal > 0 ? Math.ceil(previousTotal / pagination.pageSize) : 1
      const newLastPage = pagination.total > 0 ? Math.ceil(pagination.total / pagination.pageSize) : 1
      const isIdSort = sortBy === 'id'
      const wasOnLastPage = previousPage >= previousLastPage - 1
      const hasNewData = pagination.total > previousTotal
      
      if (isIdSort && wasOnLastPage && hasNewData) {
        if (sortOrder === 'ascending') {
          if (newLastPage !== pagination.page) {
            pagination.page = newLastPage
            const lastPageParams = {
              page: newLastPage,
              pageSize: pagination.pageSize,
              filters: requestFilters,
              sortBy: sortBy,
              sortOrder: sortOrder
            }
            const lastPageResponse = await dataApi.getList(lastPageParams)
            tableData.value = lastPageResponse.list
            pagination.page = lastPageResponse.page
            await nextTick()
          }
        } else if (sortOrder === 'descending') {
          if (pagination.page !== 1) {
            pagination.page = 1
            const firstPageParams = {
              page: 1,
              pageSize: pagination.pageSize,
              filters: requestFilters,
              sortBy: sortBy,
              sortOrder: sortOrder
            }
            const firstPageResponse = await dataApi.getList(firstPageParams)
            tableData.value = firstPageResponse.list
            pagination.page = firstPageResponse.page
            await nextTick()
          }
        }
      }
    }

    if (selectedRowId.value !== null && shouldKeepSelected) {
      const selectedRow = tableData.value.find(row => row.id === selectedRowId.value)
      if (selectedRow && tableRef.value) {
        tableRef.value.setCurrentRow(selectedRow)
        await nextTick()
        // Use dual approach for scrolling: immediate and delayed
        tableRef.value.scrollToRow(selectedRow)
        setTimeout(() => {
          if (tableRef.value) {
            tableRef.value.scrollToRow(selectedRow)
          }
        }, 300) // Increase delay for virtual scroll stabilization
      }
    }
  } catch (error: any) {
    if (!silent) ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
    silentLoading.value = false
  }
}

const handleVxeExpandChange: VxeTableEvents.ToggleRowExpand<TableData> = async ({ row, expanded }) => {
  if (expanded) {
    if (rowDetails[row.id]) return
    rowDetailsLoading[row.id] = true
    try {
      const detail = await dataApi.getRowDetail(row)
      rowDetails[row.id] = detail
    } catch (error: any) {
      rowDetailsError[row.id] = error?.message || '加载详情失败'
    } finally {
      rowDetailsLoading[row.id] = false
    }
  }
}

const handleVxeCellClick: VxeTableEvents.CellClick<TableData> = ({ row }) => {
  selectedRowId.value = row.id
}

const handleVxeSortChange: VxeTableEvents.SortChange<TableData> = ({ property, order }) => {
  if (property && order) {
    sortInfo.prop = property
    sortInfo.order = order === 'asc' ? 'ascending' : 'descending'
  } else {
    sortInfo.prop = 'id'
    sortInfo.order = 'ascending'
  }
  loadData(selectedRowId.value !== null)
}

// 处理 vxe-table 原生筛选变化
const handleVxeFilterChange: VxeTableEvents.FilterChange<TableData> = () => {
  // 重新加载数据，回到第一页
  pagination.page = 1
  loadData(selectedRowId.value !== null)
}

const handleReset = () => {
  if (tableRef.value) {
    tableRef.value.clearFilter()
    
    // 针对数值类型列，手动恢复其数据结构，防止 clearFilter 导致的 undefined 错误
    columnConfig.value.forEach(col => {
      if (col.filterable && col.filterType === 'number') {
        const column = tableRef.value?.getColumnByField(col.prop)
        if (column && column.filters && column.filters.length > 0) {
          column.filters[0].data = { filters: [{ operator: '=', value: '' }], logic: 'AND' }
        }
      }
    })
  }
  sortInfo.prop = 'id'
  sortInfo.order = 'ascending'
  loadData(true)
}

const handlePageChange = (page: number) => {
  pagination.page = page
  loadData(false)
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  loadData(selectedRowId.value !== null)
}

const getColumnWidth = (col: ColumnConfig) => columnWidths[col.prop] || col.width || null

const getFilterOptions = (prop: string) => {
  // 优先使用动态加载的选项
  if (filterOptions[prop] && filterOptions[prop].length > 0) {
    return filterOptions[prop]
  }
  // 其次使用列配置自带的选项
  const col = columnConfig.value.find(c => c.prop === prop)
  return col?.options || []
}

let lastFilterRefreshTime = 0
const FILTER_REFRESH_THROTTLE = 1000 // 降低到 1 秒

const refreshFilterOptions = async (force = false) => {
  const now = Date.now()
  if (!force && now - lastFilterRefreshTime < FILTER_REFRESH_THROTTLE) {
    return
  }
  
  try {
    const options = await dataApi.getFilterOptions()
    if (options && typeof options === 'object') {
      Object.keys(options).forEach(prop => {
        filterOptions[prop] = options[prop]
      })
    }
    lastFilterRefreshTime = now
  } catch (error) {
    console.error('Refresh filter options failed:', error)
  }
}

const getFilterPopoverWidth = (filterType: string) => filterType === 'number' ? 320 : 250

const loadStatistics = async () => {
  statisticsLoading.value = true
  try {
    statisticsData.value = await dataApi.getStatistics()
  } catch (error: any) {
    ElMessage.error('加载统计信息失败')
  } finally {
    statisticsLoading.value = false
  }
}

const handleShowStatistics = () => {
  showStatisticsDialog.value = true
  loadStatistics()
}

const handleOpenColumnSettings = () => {
  if (tableRef.value) {
    tableRef.value.openCustom()
  }
}

// 核心修复：确保重置后数据结构依然存在
const ensureFilterData = (option: any, col: ColumnConfig) => {
  if (!option) return false
  if (option.data === null || option.data === undefined || option.data === '') {
    if (col.filterType === 'number') {
      option.data = { filters: [{ operator: '=', value: '' }], logic: 'AND' }
    } else if (col.filterType === 'multi-select') {
      option.data = []
    } else {
      option.data = ''
    }
  }
  return true
}

const getDetailColumns = (detailData: RowDetail) => {
  if (!detailData || detailData.length === 0) return []
  const allKeys = new Set<string>()
  detailData.forEach(item => {
    Object.keys(item).forEach(key => {
      // 过滤掉 VXETable 内部使用的 key
      if (!key.startsWith('_X_')) {
        allKeys.add(key)
      }
    })
  })
  return Array.from(allKeys).map(key => ({ prop: key, label: key, minWidth: 150, class: 'detail-value' }))
}

const exposedMethods = {
  refreshData: async () => {
    // Run both data and filter options refresh in parallel to reduce delay
    await Promise.all([
      loadData(false, true),
      refreshFilterOptions()
    ])
  },
  refreshColumns: loadColumnsConfig
}

defineExpose(exposedMethods)

// 核心修复：处理隐藏 Tab 切换导致的卡死或布局错乱
const isVisible = ref(true)
let visibilityObserver: IntersectionObserver | null = null

const handleResize = () => {
  if (isVisible.value && tableRef.value) {
    tableRef.value.recalculate()
  }
}

const initVisibilityObserver = () => {
  const root = document.getElementById(vxeTableId.value)?.parentElement
  if (!root || !window.IntersectionObserver) return

  visibilityObserver = new IntersectionObserver((entries) => {
    const entry = entries[0]
    const wasVisible = isVisible.value
    isVisible.value = entry.isIntersecting
    
    // 当从隐藏切换到显示时，强制重绘表格
    if (isVisible.value && !wasVisible) {
      nextTick(() => {
        if (tableRef.value) {
          tableRef.value.recalculate()
          console.log('Table visibility changed to visible, recalculated.')
        }
      })
    }
  }, { threshold: 0.01 })

  visibilityObserver.observe(root)
  window.addEventListener('resize', handleResize)
}

onMounted(async () => {
  // 初始化 ID
  const tid = getTableId()
  vxeTableId.value = tid ? `vxe_table_${tid}` : 'vxe_data_table'
  
  await loadColumnsConfig()
  await loadData()
  
  // 初始化可见性观察者
  nextTick(() => {
    initVisibilityObserver()
  })
  
  // 等待一下确保 DOM 完全渲染
  await nextTick()
  await nextTick()
})

onUnmounted(() => {
  if (visibilityObserver) {
    visibilityObserver.disconnect()
    visibilityObserver = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.table-card {
  margin: 0;
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  padding: 16px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.table-container {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

.expand-detail {
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
  min-height: 60px;
  width: fit-content;
  max-width: calc(100% - 16px);
}

.loading-message,
.error-message {
  text-align: center;
  padding: 20px;
  color: #909399;
}

.bytes-display {
  font-family: monospace;
  font-size: 12px;
  color: #409eff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: help;
}

/* VXE 原生筛选面板样式定制 */
.vxe-filter-custom-panel {
  background-color: #fff;
  padding: 12px;
  min-width: 240px;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.filter-header {
  font-weight: 600;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.filter-body {
  margin-bottom: 12px;
}

.filter-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.number-filter-item {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
  align-items: center;
}

.logic-switch {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.list-column-tag {
  display: inline-block;
  padding: 0 8px;
  height: 20px;
  line-height: 18px;
  font-size: 12px;
  color: #409eff;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 4px;
  white-space: nowrap;
}

.silent-loading-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #409eff 0%, #66b1ff 50%, #409eff 100%);
  background-size: 200% 100%;
  animation: loading-bar 1.5s ease-in-out infinite;
  z-index: 2000;
}

@keyframes loading-bar {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 分页跳转输入框悬停图标 */
:deep(.el-pagination__jump),
:deep(.el-pagination__jump *),
:deep(.el-pagination__jump .el-input),
:deep(.el-pagination__jump .el-input__inner),
:deep(.el-pagination__jump .el-input__wrapper),
:deep(.el-pagination__jump input) {
  cursor: pointer !important;
}

:deep(.el-pagination__jump .el-input__inner),
:deep(.el-pagination__jump input) {
  color: #303133 !important;
  background-color: #fff !important;
  opacity: 1 !important;
  -webkit-text-fill-color: #303133 !important;
}

/* VXETable Styles */
:deep(.vxe-table--render-default .vxe-body--row.row--current) {
  background-color: #ecf5ff !important;
  color: #409eff;
  font-weight: bold;
}

:deep(.vxe-table--render-default .vxe-body--row.row--current .vxe-body--column) {
  border-top: 1px solid #409eff !important;
  border-bottom: 1px solid #409eff !important;
}

:deep(.vxe-table--render-default .vxe-body--row.row--current .vxe-body--column:first-child) {
  border-left: 4px solid #409eff !important;
}

:deep(.vxe-table--render-default .vxe-body--column.col--ellipsis) {
  height: 24px;
}
:deep(.vxe-table--render-default .vxe-cell) {
  padding-top: 0;
  padding-bottom: 0;
  line-height: 24px;
}

/* 将过滤按钮移动到左边 */
:deep(.vxe-header--column .vxe-cell) {
  display: flex;
  align-items: center;
}

:deep(.vxe-header--column .vxe-cell--title) {
  order: 2;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.vxe-header--column .vxe-cell--filter) {
  order: 1;
  margin-right: 4px;
}

:deep(.vxe-header--column .vxe-cell--sort) {
  order: 3;
  cursor: pointer;
  min-width: 14px;
  display: flex;
  justify-content: center;
}
</style>
