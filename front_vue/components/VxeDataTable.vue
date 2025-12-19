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
          layout="total, sizes, prev, pager, next, jumper"
          background
          :prev-icon="ArrowLeft"
          :next-icon="ArrowRight"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
      <!-- Right: Statistics, VXE Native Custom, Reset -->
      <div style="display: flex; gap: 12px; align-items: center;">
        <span style="font-size: 12px; color: #909399; margin-right: 8px;">(VXETable Virtual Scroll)</span>
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
        id="vxe_data_table"
        :data="tableData"
        :loading="loading && !silentLoading"
        stripe
        border
        size="mini"
        height="100%"
        auto-resize
        show-overflow="ellipsis"
        show-header-overflow="ellipsis"
        highlight-current-row
        :row-config="{ isHover: true, keyField: 'id' }"
        :column-config="{ resizable: true, fit: true }"
        :custom-config="{ storage: true, immediate: true }"
        :toolbar-config="{ custom: true }"
        :scroll-y="{ enabled: true, gt: 0 }"
        @sort-change="handleVxeSortChange"
        @cell-click="handleVxeCellClick"
        @toggle-row-expand="handleVxeExpandChange"
      >
        <!-- 展开列 -->
        <vxe-column type="expand" width="50" fixed="left">
          <template #content="{ row }">
            <div class="expand-detail" v-loading="rowDetailsLoading[row.id]">
              <template v-if="rowDetails[row.id] && rowDetails[row.id].length > 0">
                <vxe-table :data="rowDetails[row.id]" border size="small" style="width: 100%">
                  <vxe-column 
                    v-for="column in getDetailColumns(rowDetails[row.id])" 
                    :key="column.prop"
                    :field="column.prop" 
                    :title="column.label" 
                    :min-width="column.minWidth || 150"
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
            :width="getColumnWidth(col)"
            :fixed="col.fixed"
            :sortable="col.sortable"
            :visible="col.prop !== 'id'"
          >
            <template #header>
              <div class="column-header">
                <div class="header-title-row">
                  <el-popover
                    v-if="col.filterable && col.filterType !== 'none'"
                    placement="bottom"
                    :width="getFilterPopoverWidth(col.filterType || 'text')"
                    :trigger="col.filterType === 'multi-select' ? 'manual' : 'click'"
                    v-model:visible="popoverVisible[col.prop]"
                    :popper-options="col.filterType === 'number' || col.filterType === 'multi-select' ? { modifiers: [{ name: 'preventOverflow', options: { padding: 8 } }, { name: 'computeStyles', options: { gpuAcceleration: false } }] } : undefined"
                    :hide-after="0"
                    @click.stop
                  >
                    <template #reference>
                      <el-icon 
                        class="filter-icon" 
                        :style="{ color: hasActiveFilter(col.prop) ? '#409eff' : '#c0c4cc' }"
                        @click.stop="() => { 
                          if (col.filterType === 'multi-select') { 
                            popoverVisible[col.prop] = !popoverVisible[col.prop]
                            if (popoverVisible[col.prop]) {
                              keepOpenPopovers.add(col.prop)
                            } else {
                              keepOpenPopovers.delete(col.prop)
                            }
                          } 
                        }"
                      >
                        <Filter />
                      </el-icon>
                    </template>
                    <div class="filter-popover" @click.stop>
                      <div style="margin-bottom: 8px; font-weight: 600;">{{ col.label }}筛选</div>
                      
                      <!-- 文本筛选 -->
                      <template v-if="col.filterType === 'text'">
                        <el-input
                          v-model="filterInputs[col.prop]"
                          :placeholder="`筛选${col.label}（按回车确认）`"
                          size="small"
                          clearable
                          @keyup.enter="() => handleFilterChange(col.prop)"
                          @clear="() => handleFilterChange(col.prop)"
                        >
                          <template #prefix>
                            <el-icon style="font-size: 12px;"><Search /></el-icon>
                          </template>
                        </el-input>
                      </template>
                      
                      <!-- 数字筛选（单条件） -->
                      <template v-else-if="col.filterType === 'number' && !isMultiNumberFilter(col.prop)">
                        <div style="display: flex; gap: 8px; align-items: center;">
                          <el-select
                            v-model="filterInputs[`${col.prop}Operator`]"
                            placeholder="操作符"
                            size="small"
                            clearable
                            style="width: 80px"
                            :teleported="false"
                            @click.stop
                            popper-class="filter-select-dropdown"
                          >
                            <el-option label="=" value="=" />
                            <el-option label=">" value=">" />
                            <el-option label="<" value="<" />
                            <el-option label=">=" value=">=" />
                            <el-option label="<=" value="<=" />
                          </el-select>
                          <el-input
                            v-model="filterInputs[`${col.prop}Value`]"
                            placeholder="值（支持0x16进制）"
                            size="small"
                            style="flex: 1"
                            @keyup.enter="() => handleFilterChange(col.prop)"
                            @click.stop
                          />
                        </div>
                        <div style="margin-top: 4px; font-size: 12px; color: #909399;">
                          支持十进制或16进制（如：123 或 0x123）
                        </div>
                        <div style="margin-top: 8px;">
                          <el-button type="primary" size="small" @click="() => handleFilterChange(col.prop)" style="width: 100%">应用筛选</el-button>
                        </div>
                      </template>
                      
                      <!-- 数字筛选（多条件） -->
                      <template v-else-if="col.filterType === 'number' && isMultiNumberFilter(col.prop)">
                        <div class="filter-group">
                          <div
                            v-for="(filter, index) in filterInputs[`${col.prop}Filters`]"
                            :key="index"
                            style="display: flex; gap: 8px; margin-top: 8px; align-items: center"
                          >
                            <el-select
                              v-if="index > 0"
                              v-model="filterInputs[`${col.prop}Logic`]"
                              size="small"
                              style="width: 60px"
                              :teleported="false"
                              @click.stop
                              popper-class="filter-select-dropdown"
                            >
                              <el-option label="AND" value="AND" />
                              <el-option label="OR" value="OR" />
                            </el-select>
                            <el-select
                              v-model="filter.operator"
                              placeholder="操作符"
                              size="small"
                              clearable
                              style="width: 80px"
                              :teleported="false"
                              @click.stop
                              popper-class="filter-select-dropdown"
                            >
                              <el-option label="=" value="=" />
                              <el-option label=">" value=">" />
                              <el-option label="<" value="<" />
                              <el-option label=">=" value=">=" />
                              <el-option label="<=" value="<=" />
                            </el-select>
                            <el-input
                              v-model="filter.value"
                              placeholder="值（支持0x16进制）"
                              size="small"
                              style="flex: 1; min-width: 80px"
                              @keyup.enter="() => handleFilterChange(col.prop)"
                              @click.stop
                            />
                            <el-button
                              v-if="filterInputs[`${col.prop}Filters`].length > 1"
                              :icon="Delete"
                              size="small"
                              text
                              type="danger"
                              @click.stop="removeNumberFilter(col.prop, index)"
                            />
                          </div>
                          <el-button
                            size="small"
                            text
                            type="primary"
                            style="margin-top: 8px; width: 100%"
                            @click.stop="addNumberFilter(col.prop)"
                          >
                            + 添加条件
                          </el-button>
                        </div>
                        <div style="margin-top: 4px; font-size: 12px; color: #909399;">
                          支持十进制或16进制（如：123 或 0x123）
                        </div>
                        <div style="margin-top: 8px;">
                          <el-button type="primary" size="small" @click="() => handleFilterChange(col.prop)" style="width: 100%">应用筛选</el-button>
                        </div>
                      </template>
                      
                      <!-- 多选筛选 -->
                      <template v-else-if="col.filterType === 'multi-select'">
                        <el-select
                          v-model="filterInputs[col.prop]"
                          :placeholder="`筛选${col.label}（可多选）`"
                          size="small"
                          clearable
                          multiple
                          collapse-tags
                          collapse-tags-tooltip
                          style="width: 100%"
                          :teleported="false"
                          popper-class="filter-select-dropdown-keep-open"
                          @change="() => handleMultiSelectChange(col.prop)"
                          @visible-change="(visible: boolean) => { 
                            if (!visible && keepOpenPopovers.has(col.prop)) {
                              nextTick(() => {
                                popoverVisible[col.prop] = true
                              })
                            }
                          }"
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
                          v-model="filterInputs[col.prop]"
                          :placeholder="col.prop === 'ts' ? '支持文本匹配：日期、时间或日期时间（按回车确认）' : 'YYYY-MM-DD（按回车确认）'"
                          size="small"
                          clearable
                          @keyup.enter="() => handleFilterChange(col.prop)"
                          @clear="() => handleFilterChange(col.prop)"
                        />
                        <div v-if="col.prop === 'ts'" style="margin-top: 4px; font-size: 12px; color: #909399;">
                          支持文本匹配：日期、时间或日期时间（如：2024-01-01、12:30:45 或 2024-01-01 12:30:45.123456）
                        </div>
                        <div style="margin-top: 8px;">
                          <el-button type="primary" size="small" @click="() => handleFilterChange(col.prop)" style="width: 100%">应用筛选</el-button>
                        </div>
                      </template>
                    </div>
                  </el-popover>
                  <span>{{ col.label }}</span>
                </div>
              </div>
            </template>
            <template #default="{ row }">
              <template v-if="col.filterType === 'multi-select'">
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
import { Search, Refresh, Delete, Setting, ArrowDown, ArrowUp, Sort, Filter, ArrowLeft, ArrowRight, DataAnalysis } from '@element-plus/icons-vue'
import { TableData, FilterParams, NumberFilter, RowDetail, ColumnConfig } from '../types'
import type { FormInstance } from 'element-plus'
import type { VxeTableInstance, VxeTableEvents } from 'vxe-table'
import axios from 'axios'

// Props definition
const props = defineProps<{
  apiUrl: string
}>()

// 获取 tableId 从 DOM
const getTableId = (): string | null => {
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

// 拖拽相关
const dragIndex = ref<number | null>(null)
const columnListRef = ref<HTMLElement | null>(null)

const popoverVisible = reactive<Record<string, boolean>>({})
const keepOpenPopovers = reactive<Set<string>>(new Set())

const keepPopoverOpen = () => {
  if (keepOpenPopovers.size === 0) return
  keepOpenPopovers.forEach(prop => {
    if (!popoverVisible[prop]) popoverVisible[prop] = true
  })
}

let keepOpenInterval: number | null = null

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  const isInsidePopover = target.closest('.el-popover') || target.closest('.el-select-dropdown') || target.closest('.el-popper')
  const isFilterIcon = target.closest('.filter-icon')
  if (!isInsidePopover && !isFilterIcon) {
    Object.keys(popoverVisible).forEach(prop => {
      popoverVisible[prop] = false
    })
    keepOpenPopovers.clear()
  }
}

onMounted(() => {
  keepOpenInterval = setInterval(keepPopoverOpen, 100) as unknown as number
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (keepOpenInterval !== null) clearInterval(keepOpenInterval)
  document.removeEventListener('click', handleClickOutside)
})

const filterInputs = reactive<Record<string, any>>({})
const filterForm = reactive<Record<string, any>>({})

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
    columnConfig.value = config.columns
    initFilterForm(config.columns)
    await refreshFilterOptions()
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
    
    columnConfig.value.forEach(col => {
      if (!col.filterable) return
      const prop = col.prop
      switch (col.filterType) {
        case 'number':
          if (prop === 'id') {
            const operator = filterForm[`${prop}Operator`]
            const value = filterForm[`${prop}Value`]
            if (operator && value !== undefined) filters[prop] = { operator, value }
          } else {
            const propFilters = filterForm[`${prop}Filters`]
            if (Array.isArray(propFilters) && propFilters.length > 0) {
              const validFilters = propFilters.filter((f: any) => f && f.operator && f.value !== undefined)
              if (validFilters.length > 0) {
                if (validFilters.length === 1) filters[prop] = validFilters[0]
                else filters[prop] = { filters: validFilters, logic: filterForm[`${prop}Logic`] || 'AND' }
              }
            }
          }
          break
        case 'text':
        case 'date':
          const textValue = filterForm[prop]
          if (textValue) filters[prop] = textValue
          break
        case 'multi-select':
        case 'select':
          const selectValue = filterForm[prop]
          if (Array.isArray(selectValue) && selectValue.length > 0) {
            filters[prop] = selectValue.length === 1 ? selectValue[0] : selectValue
          } else if (selectValue !== undefined && selectValue !== null && selectValue !== '') {
            filters[prop] = selectValue
          }
          break
      }
    })

    const requestFilters = Object.keys(filters).length > 0 ? filters : undefined
    
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
  // Try to keep selected row visible after sorting
  loadData(selectedRowId.value !== null)
}

const initFilterForm = (columns: ColumnConfig[]) => {
  columns.forEach(col => {
    if (!col.filterable) return
    switch (col.filterType) {
      case 'number':
        if (col.prop === 'id') {
          filterForm[`${col.prop}Operator`] = undefined
          filterForm[`${col.prop}Value`] = undefined
          filterInputs[`${col.prop}Operator`] = undefined
          filterInputs[`${col.prop}Value`] = undefined
        } else {
          filterForm[`${col.prop}Filters`] = [{ operator: undefined, value: undefined }]
          filterForm[`${col.prop}Logic`] = 'AND'
          filterInputs[`${col.prop}Filters`] = [{ operator: undefined, value: undefined }]
          filterInputs[`${col.prop}Logic`] = 'AND'
        }
        break
      case 'multi-select':
      case 'select':
        const defaultValue = col.filterType === 'multi-select' ? [] : undefined
        filterForm[col.prop] = defaultValue
        filterInputs[col.prop] = col.filterType === 'multi-select' ? [] : undefined
        if (col.options && col.options.length > 0) filterOptions[col.prop] = col.options
        break
      case 'text':
      case 'date':
        filterForm[col.prop] = undefined
        filterInputs[col.prop] = undefined
        break
    }
  })
}

const syncFilterInputsToForm = () => {
  Object.keys(filterInputs).forEach(key => {
    const value = filterInputs[key]
    if (Array.isArray(value)) {
      if (key.endsWith('Filters')) filterForm[key] = value.map((f: any) => ({ ...f }))
      else filterForm[key] = [...value]
    } else filterForm[key] = value
  })
}

const handleFilterChange = (prop?: string) => {
  syncFilterInputsToForm()
  nextTick(() => {
    loadData(true)
    if (prop) {
      keepOpenPopovers.delete(prop)
      popoverVisible[prop] = false
    }
  })
}

const handleMultiSelectChange = (prop: string) => {
  keepOpenPopovers.add(prop)
  popoverVisible[prop] = true
  syncFilterInputsToForm()
  nextTick(() => {
    popoverVisible[prop] = true
    loadData(true)
  })
  setTimeout(() => { popoverVisible[prop] = true }, 50)
}

const isMultiNumberFilter = (prop: string) => prop !== 'id'

const addNumberFilter = (prop: string) => {
  const filtersKey = `${prop}Filters`
  if (!Array.isArray(filterInputs[filtersKey])) filterInputs[filtersKey] = []
  filterInputs[filtersKey].push({ operator: undefined, value: undefined })
}

const removeNumberFilter = (prop: string, index: number) => {
  const filtersKey = `${prop}Filters`
  if (Array.isArray(filterInputs[filtersKey])) {
    filterInputs[filtersKey].splice(index, 1)
    if (filterInputs[filtersKey].length === 0) addNumberFilter(prop)
  }
}

const handleReset = () => {
  columnConfig.value.forEach(col => {
    if (!col.filterable) return
    const prop = col.prop
    switch (col.filterType) {
      case 'number':
        if (prop === 'id') {
          filterInputs[`${prop}Operator`] = undefined
          filterInputs[`${prop}Value`] = undefined
        } else {
          filterInputs[`${prop}Filters`] = [{ operator: undefined, value: undefined }]
          filterInputs[`${prop}Logic`] = 'AND'
        }
        break
      case 'multi-select':
        filterInputs[prop] = []
        break
      default:
        filterInputs[prop] = undefined
        break
    }
  })
  syncFilterInputsToForm()
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

const hasActiveFilter = (prop: string) => {
  const col = columnConfig.value.find(c => c.prop === prop)
  if (!col || !col.filterable) return false
  switch (col.filterType) {
    case 'number':
      if (prop === 'id') return !!(filterForm[`${prop}Operator`] && filterForm[`${prop}Value`] !== undefined)
      return Array.isArray(filterForm[`${prop}Filters`]) && filterForm[`${prop}Filters`].some((f: any) => f.operator && f.value !== undefined)
    case 'multi-select':
      return Array.isArray(filterForm[prop]) && filterForm[prop].length > 0
    default:
      return !!filterForm[prop]
  }
}

const getFilterOptions = (prop: string) => filterOptions[prop] || columnConfig.value.find(c => c.prop === prop)?.options || []

let lastFilterRefreshTime = 0
const FILTER_REFRESH_THROTTLE = 2000 // 2 seconds

const refreshFilterOptions = async (force = false) => {
  const now = Date.now()
  if (!force && now - lastFilterRefreshTime < FILTER_REFRESH_THROTTLE) {
    return
  }
  
  try {
    const options = await dataApi.getFilterOptions()
    Object.keys(options).forEach(prop => { filterOptions[prop] = options[prop] })
    lastFilterRefreshTime = now
  } catch (error) {}
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

const getDetailColumns = (detailData: RowDetail) => {
  if (!detailData || detailData.length === 0) return []
  const allKeys = new Set<string>()
  detailData.forEach(item => Object.keys(item).forEach(key => allKeys.add(key)))
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

// 注册到全局注册表的函数
const registerToGlobalRegistry = () => {
  const root = document.getElementById('root')
  const tableId = root?.dataset.tableId
  
  if (tableId) {
    if (!(window as any).__nice_table_registry) {
      (window as any).__nice_table_registry = {}
    }
    
    const registry = (window as any).__nice_table_registry
    registry[tableId] = exposedMethods
    console.log('VxeDataTable: NiceTable instance registered:', tableId, registry)
    
    window.dispatchEvent(new CustomEvent('nice-table-ready', { detail: { tableId } }))
    return true
  }
  return false
}

onMounted(async () => {
  await loadColumnsConfig()
  await loadData()
  
  // 等待一下确保 DOM 完全渲染后注册
  await nextTick()
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 300))
  
  if (!registerToGlobalRegistry()) {
    let retries = 0
    const maxRetries = 30
    const interval = setInterval(() => {
      retries++
      if (registerToGlobalRegistry() || retries >= maxRetries) {
        clearInterval(interval)
      }
    }, 200)
  }
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

.column-header {
  display: flex;
  flex-direction: column;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-icon {
  cursor: pointer;
  font-size: 14px;
}

.filter-icon:hover {
  color: #409eff !important;
}

.filter-popover {
  padding: 4px 0;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.expand-detail {
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 4px;
  min-height: 100px;
}

.loading-message,
.error-message {
  text-align: center;
  padding: 20px;
  color: #909399;
}

.column-settings-content {
  max-height: 500px;
  overflow-y: auto;
}

.column-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.column-item {
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fff;
}

.column-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
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
  height: 28px;
}
:deep(.vxe-table--render-default .vxe-cell) {
  padding-top: 0;
  padding-bottom: 0;
}
</style>
