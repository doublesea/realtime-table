<template>
  <el-card class="table-card" :body-style="{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }">
    <!-- 工具栏 -->
    <div class="toolbar" style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
      <!-- Left: Pagination -->
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[50, 100, 200, 500]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          background
          :prev-icon="ArrowLeft"
          :next-icon="ArrowRight"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
      <!-- Right: Statistics, Column Settings, Reset -->
      <div style="display: flex; gap: 12px; align-items: center;">
        <el-button :icon="DataAnalysis" size="small" @click="handleShowStatistics">
          统计
        </el-button>
        <el-button :icon="Setting" size="small" @click="showColumnSettings = true">
          列设置
        </el-button>
        <el-button :icon="Refresh" size="small" @click="handleReset">重置所有筛选</el-button>
      </div>
    </div>

    <!-- 数据表格容器 -->
    <div class="table-container">
      <!-- 轻量级加载指示器（顶部进度条） -->
      <div v-if="silentLoading" class="silent-loading-bar"></div>
      <el-table
        ref="tableRef"
        :data="tableData"
        v-loading="loading && !silentLoading"
        stripe
        border
        height="100%"
        style="width: 100%; table-layout: fixed"
        class="table-with-transition"
      @sort-change="handleSortChange"
      @row-click="handleRowClick"
      @expand-change="handleExpandChange"
      highlight-current-row
      :row-class-name="getRowClassName"
    >
      <!-- 展开列 -->
      <el-table-column type="expand" width="50" fixed="left">
        <template #default="{ row }">
          <div class="expand-detail" v-loading="rowDetailsLoading[row.id]">
            <template v-if="rowDetails[row.id] && rowDetails[row.id].length > 0">
              <el-table :data="rowDetails[row.id]" border size="small" style="width: 100%">
                <el-table-column 
                  v-for="column in getDetailColumns(rowDetails[row.id])" 
                  :key="column.prop"
                  :prop="column.prop" 
                  :label="column.label" 
                  :min-width="column.minWidth || 150"
                  align="left"
                >
                  <template #default="{ row: detailRow }">
                    <span :class="column.class">{{ detailRow[column.prop] ?? '-' }}</span>
                  </template>
                </el-table-column>
              </el-table>
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
      </el-table-column>
      <!-- 动态生成列（使用排序后的列顺序） -->
      <template v-for="col in orderedColumns" :key="col.prop">
        <el-table-column
          v-if="columnVisible[col.prop]"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.minWidth || 120"
          :width="getColumnWidth(col)"
          :fixed="col.fixed"
          :sortable="col.sortable ? 'custom' : false"
          :show-overflow-tooltip="true"
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
                        // 当 el-select 的下拉框关闭时，确保 popover 不关闭
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
              <el-icon 
                v-if="col.sortable"
                class="sort-icon" 
                :style="{ color: getSortIconColor(col.prop) }"
                @click.stop="handleHeaderSortClick(col.prop)"
              >
                <component :is="getSortIcon(col.prop)" />
              </el-icon>
            </div>
          </div>
          <!-- 列宽调整手柄 -->
          <div
            class="column-resize-handle"
            @mousedown="handleResizeStart($event, col.prop)"
            @dblclick="handleResizeAuto(col.prop)"
          ></div>
        </template>
        <template #default="scope">
          <template v-if="col.filterType === 'multi-select'">
            <el-tag>
              {{ scope.row[col.prop] ?? '-' }}
            </el-tag>
          </template>
          <template v-else-if="col.type === 'bytes'">
            <span class="bytes-display" :title="scope.row[col.prop]">
              {{ scope.row[col.prop] ?? '-' }}
            </span>
          </template>
          <template v-else>
            {{ scope.row[col.prop] ?? '-' }}
          </template>
        </template>
        </el-table-column>
      </template>
      </el-table>
    </div>

    <!-- 列设置弹窗 -->
    <el-dialog
      v-model="showColumnSettings"
      title="列设置"
      width="500px"
      :close-on-click-modal="false"
    >
      <div class="column-settings-content">
        <div style="margin-bottom: 12px; color: #909399; font-size: 12px;">
          拖拽左侧图标可调整列顺序，勾选可控制列的显示/隐藏
        </div>
        <div class="column-list" ref="columnListRef">
          <div
            v-for="(col, index) in orderedColumns"
            :key="col.prop"
            class="column-item"
            :draggable="true"
            :data-index="index"
            @dragstart="handleDragStart($event, index)"
            @dragover.prevent="handleDragOver($event, index)"
            @drop="handleDrop($event, index)"
            @dragend="handleDragEnd"
          >
            <div class="column-item-content">
              <el-icon class="drag-handle" :class="{ 'dragging': dragIndex === index }">
                <Rank />
              </el-icon>
              <el-checkbox
                v-model="columnVisible[col.prop]"
                @change="() => handleColumnToggle(col.prop)"
                @click.stop
              >
                {{ col.label }}
              </el-checkbox>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showColumnSettings = false">取消</el-button>
        <el-button type="primary" @click="handleSaveColumnOrder">确定</el-button>
      </template>
    </el-dialog>

    <!-- 统计信息弹窗 -->
    <el-dialog
      v-model="showStatisticsDialog"
      title="数据统计"
      width="600px"
      :close-on-click-modal="true"
    >
      <div class="statistics-content" v-loading="statisticsLoading">
        <el-table 
          v-if="statisticsData.rows.length > 0" 
          :data="statisticsData.rows" 
          border 
          stripe 
          size="small"
          style="width: 100%"
        >
          <el-table-column
            v-for="col in statisticsData.columns"
            :key="col"
            :prop="col"
            :label="col"
            :min-width="col === '描述' ? 200 : 120"
          />
        </el-table>
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
import { Search, Refresh, Delete, Setting, ArrowDown, ArrowUp, Sort, Filter, Rank, ArrowLeft, ArrowRight, DataAnalysis } from '@element-plus/icons-vue'
import { TableData, FilterParams, NumberFilter, RowDetail, ColumnConfig } from '../types'
import type { ElTable } from 'element-plus'
import type { FormInstance } from 'element-plus'
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
      // 处理响应格式
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
    getRowPosition: async (row_id: any, filters?: any) => {
      const response = await client.post('/row-position', { row_id, filters })
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
const silentLoading = ref(false) // 静默加载（不显示遮罩）
const selectedRowId = ref<number | null>(null) // 选中的行ID
const tableRef = ref<InstanceType<typeof ElTable>>() // 表格引用
const filterOptions = reactive<Record<string, string[]>>({})

// 行详情数据
const rowDetails = reactive<Record<number, RowDetail>>({})
const rowDetailsLoading = reactive<Record<number, boolean>>({})
const rowDetailsError = reactive<Record<number, string>>({})

// 列配置（从后端获取）
const columnConfig = ref<ColumnConfig[]>([])

// 列显示状态（动态生成）
const columnVisible = reactive<Record<string, boolean>>({})

// 列顺序（存储列的prop顺序）
const columnOrder = ref<string[]>([])

// 列宽度（存储每列的自定义宽度）
const columnWidths = reactive<Record<string, number>>({})

// 列设置弹窗显示状态
const showColumnSettings = ref(false)

// 统计信息弹窗状态
const showStatisticsDialog = ref(false)
const statisticsLoading = ref(false)
const statisticsData = ref<{ columns: string[]; rows: Record<string, string>[] }>({ columns: [], rows: [] })

// 添加数据相关状态 (Removed add data dialog logic as per refactoring requirement to minimal component)
const showAddDataDialog = ref(false)
const addingData = ref(false)
const newDataForm = reactive<Record<string, any>>({})
const newDataFormRef = ref<FormInstance>()

// 拖拽相关状态
const dragIndex = ref<number | null>(null)
const columnListRef = ref<HTMLElement | null>(null)

// 列宽调整相关状态
const resizingColumn = ref<string | null>(null)
const resizeStartX = ref<number>(0)
const resizeStartWidth = ref<number>(0)

// 计算属性：根据列顺序排序的列配置
const orderedColumns = computed(() => {
  if (columnOrder.value.length === 0) {
    return columnConfig.value
  }
  // 按照columnOrder的顺序排序
  const orderMap = new Map(columnOrder.value.map((prop, index) => [prop, index]))
  return [...columnConfig.value].sort((a, b) => {
    const indexA = orderMap.get(a.prop) ?? Infinity
    const indexB = orderMap.get(b.prop) ?? Infinity
    return indexA - indexB
  })
})

// 计算可见列的总宽度，用于确保表格填满屏幕
const visibleColumnsCount = computed(() => {
  return orderedColumns.value.filter(col => columnVisible[col.prop]).length
})

// Popover 显示状态（用于保持多选筛选的悬浮框打开）
const popoverVisible = reactive<Record<string, boolean>>({})

// 需要保持打开的 popover（多选筛选时）
const keepOpenPopovers = reactive<Set<string>>(new Set())

// 使用定时器持续检查并保持需要打开的 popover（仅当 keepOpenPopovers 中有值时）
const keepPopoverOpen = () => {
  if (keepOpenPopovers.size === 0) return
  keepOpenPopovers.forEach(prop => {
    if (!popoverVisible[prop]) {
      popoverVisible[prop] = true
    }
  })
}

// 启动定时器，每100ms检查一次
let keepOpenInterval: number | null = null

// 处理点击外部关闭 popover
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  
  // 检查点击是否在任何 popover 内部
  // 包括 popover 本身、el-select 下拉框等
  const isInsidePopover = target.closest('.el-popover') || 
                          target.closest('.el-select-dropdown') ||
                          target.closest('.el-popper')
  
  // 检查是否点击在筛选图标上（需要排除，因为点击图标应该切换 popover）
  const isFilterIcon = target.closest('.filter-icon')
  
  // 如果点击在 popover 外部且不是筛选图标，关闭所有打开的 popover
  if (!isInsidePopover && !isFilterIcon) {
    // 关闭所有 popover（包括手动控制和自动控制的）
    Object.keys(popoverVisible).forEach(prop => {
      if (popoverVisible[prop]) {
        popoverVisible[prop] = false
      }
    })
    // 清除所有保持打开的标记
    keepOpenPopovers.clear()
  }
}

// 窗口大小变化处理
const handleResize = () => {
  initTableWidth()
}

onMounted(() => {
  keepOpenInterval = setInterval(keepPopoverOpen, 100) as unknown as number
  // 添加全局点击监听器
  document.addEventListener('click', handleClickOutside)
  // 添加窗口大小变化监听
  window.addEventListener('resize', handleResize)
})

// 组件卸载时清理定时器和监听器
onUnmounted(() => {
  if (keepOpenInterval !== null) {
    clearInterval(keepOpenInterval)
  }
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', handleResize)
})

// 初始化列显示状态和列顺序
const initColumnVisible = (columns: ColumnConfig[]) => {
  columns.forEach(col => {
    // id列默认隐藏，其他列默认显示
    columnVisible[col.prop] = col.prop !== 'id'
  })
  // 初始化列顺序
  if (columnOrder.value.length === 0) {
    columnOrder.value = columns.map(col => col.prop)
  }
}

// 临时输入状态（用户正在输入的值，不会立即触发刷新）
// 使用动态对象，根据列配置初始化
const filterInputs = reactive<Record<string, any>>({})

// 实际筛选表单（用于查询，只在确认时从 filterInputs 同步）
const filterForm = reactive<Record<string, any>>({})

const pagination = reactive({
  page: 1,
  pageSize: 100,
  total: 0
})

// 排序状态（默认按ID升序，最新的在后）
const sortInfo = reactive({
  prop: 'id' as string | undefined,
  order: 'ascending' as 'ascending' | 'descending' | null | undefined
})

// 默认列配置（当后端加载失败时使用，现在为空数组，因为字段应该是动态的）
// 如果后端配置加载失败，前端将无法显示任何列，这是预期的行为
const defaultColumns: ColumnConfig[] = []

// 加载列配置
const loadColumnsConfig = async () => {
  try {
    const config = await dataApi.getColumnsConfig()
    columnConfig.value = config.columns
    initColumnVisible(config.columns)
    initFilterForm(config.columns)
    // 加载筛选选项
    await refreshFilterOptions()
  } catch (error) {
    ElMessage.error('加载列配置失败，使用默认配置')
    // 使用默认列配置
    columnConfig.value = defaultColumns
    initColumnVisible(defaultColumns)
    initFilterForm(defaultColumns)
  }
}

// 加载数据
const loadData = async (keepSelectedRow = false, silent = false) => {
  // 如果是静默加载，只显示顶部进度条，不显示遮罩
  if (silent) {
    silentLoading.value = true
  } else {
    loading.value = true
  }
  try {
    // 保存刷新前的状态（用于判断是否需要自动跳转到最新数据）
    const previousPage = pagination.page
    const previousTotal = pagination.total
    
    const filters: FilterParams = {}
    
    // 动态构建筛选条件，基于列配置
    columnConfig.value.forEach(col => {
      if (!col.filterable) return
      
      const prop = col.prop
      
      switch (col.filterType) {
        case 'number':
          // 数字类型筛选
          if (prop === 'id') {
            // 单条件：操作符和值
            const operator = filterForm[`${prop}Operator`]
            const value = filterForm[`${prop}Value`]
            if (operator && value !== undefined) {
              filters[prop] = { operator, value }
            }
          } else {
            // 多条件：筛选器数组和逻辑
            const propFilters = filterForm[`${prop}Filters`]
            if (Array.isArray(propFilters) && propFilters.length > 0) {
              const validFilters = propFilters.filter(
                (f: any) => f && f.operator && f.value !== undefined
              )
              if (validFilters.length > 0) {
                if (validFilters.length === 1) {
                  filters[prop] = validFilters[0]
                } else {
                  filters[prop] = {
                    filters: validFilters,
                    logic: filterForm[`${prop}Logic`] || 'AND'
                  }
                }
              }
            }
          }
          break
          
        case 'text':
        case 'date':
          // 文本或日期筛选
          const textValue = filterForm[prop]
          if (textValue) {
            filters[prop] = textValue
          }
          break
          
        case 'multi-select':
        case 'select':
          // 多选或单选筛选
          const selectValue = filterForm[prop]
          if (Array.isArray(selectValue) && selectValue.length > 0) {
            filters[prop] = selectValue.length === 1 ? selectValue[0] : selectValue
          } else if (selectValue !== undefined && selectValue !== null && selectValue !== '') {
            filters[prop] = selectValue
          }
          break
      }
    })

    // 发送筛选条件（只有在有筛选条件时才发送）
    const requestFilters = Object.keys(filters).length > 0 ? filters : undefined
    
    // 如果保持选中行，需要先查询选中行在新筛选条件下的位置
    let targetPage = pagination.page
    let shouldKeepSelected = true
    if (keepSelectedRow && selectedRowId.value !== null) {
      try {
        const positionResponse = await dataApi.getRowPosition(selectedRowId.value, requestFilters)
        if (positionResponse.found) {
          // 计算选中行应该在哪一页
          targetPage = Math.floor(positionResponse.position / pagination.pageSize) + 1
        } else {
          // 选中行不在筛选结果中，清除选中状态
          selectedRowId.value = null
          shouldKeepSelected = false
        }
      } catch (error) {
        // 查询失败时，不清除选中状态，继续尝试在当前页查找
      }
    }

    // 如果没有指定排序，默认按ID升序（最新的在后）
    const sortBy = sortInfo.prop || 'id'
    const sortOrder = sortInfo.order || 'ascending'
    
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
    
    // 数据加载完成后
    await nextTick()
    
    // 强制启用分页跳转输入框
    enablePaginationJumper()
    
    // 如果是静默刷新（自动刷新），检查是否需要自动跳转到最新数据
    if (silent) {
      // 计算刷新前后的最后一页
      const previousLastPage = previousTotal > 0 ? Math.ceil(previousTotal / pagination.pageSize) : 1
      const newLastPage = pagination.total > 0 ? Math.ceil(pagination.total / pagination.pageSize) : 1
      
      // 判断是否应该自动跳转到最后一页显示最新数据
      // 条件: 按ID排序，且用户在最后一页或接近最后一页
      const isIdSort = sortBy === 'id'
      const wasOnLastPage = previousPage >= previousLastPage - 1  // 在最后一页或倒数第二页
      const hasNewData = pagination.total > previousTotal  // 有新数据添加
      
      if (isIdSort && wasOnLastPage && hasNewData) {
        if (sortOrder === 'ascending') {
          // 升序：新数据在最后，跳转到新的最后一页
          if (newLastPage !== pagination.page) {
            pagination.page = newLastPage
            // 重新加载最后一页的数据
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
          // 降序：新数据在第一页，跳转到第一页
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
      if (selectedRow) {
        if (tableRef.value) {
          tableRef.value.setCurrentRow(selectedRow)
        }
        // 滚动到选中行，确保可见（等待 DOM 更新完成）
        await nextTick()
        // 使用 setTimeout 确保表格渲染完成后再滚动
        setTimeout(() => {
          scrollToSelectedRow()
        }, 100)
      }
    }
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '加载数据失败'
    if (!silent) ElMessage.error(`加载数据失败: ${errorMsg}`)
  } finally {
    loading.value = false
    silentLoading.value = false
  }
}

// 处理行展开/收起
const handleExpandChange = async (row: TableData, expandedRows: TableData[]) => {
  // 如果行被展开
  if (expandedRows.includes(row)) {
    // 如果已经加载过详情，不再重复加载
    if (rowDetails[row.id]) {
      return
    }
    
    // 加载行详情
    rowDetailsLoading[row.id] = true
    rowDetailsError[row.id] = ''
    
    try {
      const detail = await dataApi.getRowDetail(row)
      rowDetails[row.id] = detail
    } catch (error: any) {
      const errorMsg = error?.message || '加载详情失败'
      rowDetailsError[row.id] = errorMsg
      ElMessage.error(`加载行详情失败: ${errorMsg}`)
    } finally {
      rowDetailsLoading[row.id] = false
    }
  } else {
    // 行被收起时，可以选择清除详情数据（可选，保留数据可以避免重复加载）
    // delete rowDetails[row.id]
    // delete rowDetailsLoading[row.id]
    // delete rowDetailsError[row.id]
  }
}

// 处理行点击
const handleRowClick = (row: TableData) => {
  selectedRowId.value = row.id
  // 点击后滚动到该行
  nextTick(() => {
    scrollToSelectedRow()
  })
}

// 滚动到选中行
const scrollToSelectedRow = () => {
  if (!tableRef.value || selectedRowId.value === null) {
    return
  }
  
  // 查找选中行在当前数据中的索引
  const selectedIndex = tableData.value.findIndex(row => row.id === selectedRowId.value)
  if (selectedIndex === -1) {
    return
  }
  
  try {
    const tableEl = tableRef.value.$el
    if (!tableEl) {
      return
    }
    
    // 获取表格体容器
    const tableBodyWrapper = tableEl.querySelector('.el-table__body-wrapper') as HTMLElement
    if (!tableBodyWrapper) {
      return
    }
    
    // 获取表格行元素
    const rows = tableBodyWrapper.querySelectorAll('.el-table__row')
    if (rows.length === 0 || selectedIndex >= rows.length) {
      return
    }
    
    // 获取选中行的DOM元素
    const targetRow = rows[selectedIndex] as HTMLElement
    if (!targetRow) {
      return
    }
    
    // 使用scrollIntoView方法，更简单可靠
    targetRow.scrollIntoView({
      behavior: 'smooth',
      block: 'center', // 让选中行在可视区域中间
      inline: 'nearest'
    })
  } catch (error) {
    // 如果scrollIntoView失败，尝试使用scrollTo方法
    try {
      const tableEl = tableRef.value.$el
      const tableBodyWrapper = tableEl?.querySelector('.el-table__body-wrapper') as HTMLElement
      if (tableBodyWrapper) {
        const rows = tableBodyWrapper.querySelectorAll('.el-table__row')
        const targetRow = rows[selectedIndex] as HTMLElement
        if (targetRow) {
          const rowTop = targetRow.offsetTop
          const tableHeight = tableBodyWrapper.clientHeight
          const targetScrollTop = rowTop - tableHeight / 2 + targetRow.offsetHeight / 2
          tableBodyWrapper.scrollTo({
            top: Math.max(0, targetScrollTop),
            behavior: 'smooth'
          })
        }
      }
    } catch (fallbackError) {
      // 备用方法也失败，静默处理
    }
  }
}

// 滚动到最后一行
const scrollToLastRow = () => {
  if (!tableRef.value || tableData.value.length === 0) {
    return
  }
  
  try {
    const tableEl = tableRef.value.$el
    if (!tableEl) {
      return
    }
    
    // 获取表格体容器
    const tableBodyWrapper = tableEl.querySelector('.el-table__body-wrapper') as HTMLElement
    if (!tableBodyWrapper) {
      return
    }
    
    // 获取表格行元素
    const rows = tableBodyWrapper.querySelectorAll('.el-table__row')
    if (rows.length === 0) {
      return
    }
    
    // 获取最后一行的DOM元素
    const lastRow = rows[rows.length - 1] as HTMLElement
    if (!lastRow) {
      return
    }
    
    // 滚动到最后一行
    lastRow.scrollIntoView({
      behavior: 'smooth',
      block: 'end', // 让最后一行在可视区域底部
      inline: 'nearest'
    })
  } catch (error) {
    // 如果scrollIntoView失败，尝试使用scrollTo方法
    try {
      const tableEl = tableRef.value.$el
      const tableBodyWrapper = tableEl?.querySelector('.el-table__body-wrapper') as HTMLElement
      if (tableBodyWrapper) {
        // 直接滚动到底部
        tableBodyWrapper.scrollTo({
          top: tableBodyWrapper.scrollHeight,
          behavior: 'smooth'
        })
      }
    } catch (fallbackError) {
      // 备用方法也失败，静默处理
    }
  }
}

// 获取行样式类名（用于高亮选中行）
const getRowClassName = ({ row }: { row: TableData }) => {
  return row.id === selectedRowId.value ? 'selected-row' : ''
}

// 根据详情数据动态获取列配置
const getDetailColumns = (detailData: RowDetail) => {
  if (!detailData || detailData.length === 0) {
    return []
  }
  
  // 获取所有可能的字段名
  const allKeys = new Set<string>()
  detailData.forEach(item => {
    Object.keys(item).forEach(key => {
      // 过滤掉内部使用的 key
      if (!key.startsWith('_X_')) {
        allKeys.add(key)
      }
    })
  })
  
  // 将字段名转换为列配置，直接使用原始key作为标题
  const columns = Array.from(allKeys).map(key => {
    return {
      prop: key,
      label: key,  // 直接使用原始key作为列标题
      minWidth: 150,
      class: 'detail-value'
    }
  })
  
  return columns
}

// 动态初始化filterForm和filterInputs结构
const initFilterForm = (columns: ColumnConfig[]) => {
  // 清空现有的filterForm和filterInputs
  Object.keys(filterForm).forEach(key => {
    delete filterForm[key]
  })
  Object.keys(filterInputs).forEach(key => {
    delete filterInputs[key]
  })
  
  // 根据列配置动态初始化filterForm和filterInputs
  columns.forEach(col => {
    if (!col.filterable) return
    
    switch (col.filterType) {
      case 'number':
        // 数字类型：判断是否需要多条件筛选（默认只有id使用单条件，其他使用多条件）
        if (col.prop === 'id') {
          // 单条件：操作符和值
          filterForm[`${col.prop}Operator`] = undefined
          filterForm[`${col.prop}Value`] = undefined
          filterInputs[`${col.prop}Operator`] = undefined
          filterInputs[`${col.prop}Value`] = undefined
        } else {
          // 多条件：筛选器数组和逻辑
          filterForm[`${col.prop}Filters`] = [{ operator: undefined, value: undefined }]
          filterForm[`${col.prop}Logic`] = 'AND'
          filterInputs[`${col.prop}Filters`] = [{ operator: undefined, value: undefined }]
          filterInputs[`${col.prop}Logic`] = 'AND'
        }
        break
      case 'multi-select':
      case 'select':
        // 选择类型：数组或字符串
        const defaultValue = col.filterType === 'multi-select' ? [] : undefined
        filterForm[col.prop] = defaultValue
        // 确保响应式：使用 Vue 的响应式方式设置
        if (col.filterType === 'multi-select') {
          filterInputs[col.prop] = []
        } else {
          filterInputs[col.prop] = undefined
        }
        // 初始化筛选选项
        if (col.options && col.options.length > 0) {
          filterOptions[col.prop] = col.options
        }
        break
      case 'text':
      case 'date':
        // 文本或日期类型：字符串
        filterForm[col.prop] = undefined
        filterInputs[col.prop] = undefined
        break
    }
  })
}

// 同步输入状态到筛选表单
const syncFilterInputsToForm = () => {
  // 遍历所有filterInputs的键，同步到filterForm
  Object.keys(filterInputs).forEach(key => {
    const value = filterInputs[key]
    if (Array.isArray(value)) {
      // 数组类型（多选或筛选器数组）
      if (key.endsWith('Filters')) {
        // 筛选器数组，需要深拷贝
        filterForm[key] = value.map((f: any) => ({ ...f }))
      } else {
        // 多选数组，需要浅拷贝
        filterForm[key] = [...value]
      }
    } else {
      // 其他类型直接复制
      filterForm[key] = value
    }
  })
}

// 处理筛选变化（仅在确认时调用）
const handleFilterChange = (prop?: string) => {
  // 先同步输入状态到筛选表单
  syncFilterInputsToForm()
  
  // 等待一下确保数据同步完成
  nextTick(() => {
    // 保持选中行在当前页可见
    loadData(true)
    
    // 如果有字段名，关闭该字段的悬浮框
    if (prop) {
      // 移除保持打开的标记
      keepOpenPopovers.delete(prop)
      // 关闭悬浮框
      popoverVisible[prop] = false
    }
  })
}

// 处理多选变化（立即应用筛选并保持悬浮框打开）
const handleMultiSelectChange = (prop: string) => {
  // 标记这个字段的 popover 需要保持打开
  keepOpenPopovers.add(prop)
  
  // 立即强制保持悬浮框打开
  popoverVisible[prop] = true
  
  // 立即同步输入状态到筛选表单并应用筛选
  syncFilterInputsToForm()
  
  // 在多个时机确保悬浮框保持打开
  nextTick(() => {
    popoverVisible[prop] = true
    // 应用筛选
    loadData(true)
  })
  
  // 延迟确保 DOM 更新完成
  setTimeout(() => {
    popoverVisible[prop] = true
  }, 50)
}

// 处理筛选变化并关闭悬浮框
const handleFilterChangeAndClose = (prop: string) => {
  // 移除保持打开的标记
  keepOpenPopovers.delete(prop)
  handleFilterChange()
  // 关闭悬浮框
  nextTick(() => {
    popoverVisible[prop] = false
  })
}

// 判断是否为多条件数字筛选
const isMultiNumberFilter = (prop: string) => {
  // 只有 id 使用单条件，其他数字字段使用多条件
  return prop !== 'id'
}

// 添加数字筛选条件
const addNumberFilter = (prop: string) => {
  const filtersKey = `${prop}Filters`
  if (!Array.isArray(filterInputs[filtersKey])) {
    filterInputs[filtersKey] = []
  }
  filterInputs[filtersKey].push({
    operator: undefined,
    value: undefined
  })
}

// 移除数字筛选条件
const removeNumberFilter = (prop: string, index: number) => {
  const filtersKey = `${prop}Filters`
  if (Array.isArray(filterInputs[filtersKey])) {
    filterInputs[filtersKey].splice(index, 1)
    if (filterInputs[filtersKey].length === 0) {
      addNumberFilter(prop)
    }
  }
  // 移除条件后不立即触发刷新，用户需要手动点击应用筛选
}

// 重置筛选
const handleReset = () => {
  // 根据列配置动态重置所有筛选字段
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
      case 'text':
      case 'date':
      case 'select':
        filterInputs[prop] = undefined
        break
    }
  })
  
  // 同步到筛选表单并刷新
  syncFilterInputsToForm()
  // 重置排序为默认值（ID升序，最新的在后）
  sortInfo.prop = 'id'
  sortInfo.order = 'ascending'
  // 保持选中行，不重置页码（让 loadData 自动计算选中行所在页）
  // 如果选中行存在，loadData(true) 会自动计算选中行在新筛选条件下的位置并跳转到对应页
  loadData(true) // 保持选中行
}

// 处理分页变化
const handlePageChange = (page: number) => {
  pagination.page = page
  loadData(false) // 分页变化时不保持选中行
}

// 处理每页数量变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  // 如果选中了行，计算新pageSize下应该在哪一页
  if (selectedRowId.value !== null) {
    loadData(true)
  } else {
    pagination.page = 1
    loadData(false)
  }
}

// 处理排序变化
const handleSortChange = ({ column, prop, order }: any) => {
  // Element Plus 的 order 可能是 'ascending', 'descending', null 或 undefined
  // 更新排序状态
  if (prop && order) {
    sortInfo.prop = prop
    sortInfo.order = order === 'asc' ? 'ascending' : (order === 'desc' ? 'descending' : order)
  } else {
    // 清除排序时，恢复默认排序（ID升序，最新的在后）
    sortInfo.prop = 'id'
    sortInfo.order = 'ascending'
  }
  
  // 重置到第一页
  pagination.page = 1
  // 重新加载数据
  loadData(false)
}

// 处理列显示/隐藏切换
const handleColumnToggle = (prop: string) => {
  // 如果当前是隐藏操作，检查是否只剩一列
  if (!columnVisible[prop]) {
    // 计算可见列数（不包括当前要隐藏的列）
    const visibleCount = Object.entries(columnVisible)
      .filter(([key, value]) => key !== prop && value)
      .length
    
    // 如果隐藏后没有可见列了，阻止隐藏
    if (visibleCount === 0) {
      ElMessage.warning('至少需要显示一列')
      // 恢复显示状态
      columnVisible[prop] = true
      return
    }
  }
  // 列显示状态已在 checkbox 的 v-model 中更新
  // 列显示状态变化后，重新计算表格宽度
  nextTick(() => {
    initTableWidth()
  })
}

// 拖拽处理函数
const handleDragStart = (event: DragEvent, index: number) => {
  dragIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/html', '')
  }
  // 添加拖拽样式
  const target = event.target as HTMLElement
  const item = target.closest('.column-item') as HTMLElement | null
  if (item) {
    item.style.opacity = '0.5'
  }
}

const handleDragOver = (event: DragEvent, index: number) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  // 添加悬停样式
  const target = event.target as HTMLElement
  const item = target.closest('.column-item') as HTMLElement | null
  if (item && dragIndex.value !== null && dragIndex.value !== index) {
    item.style.backgroundColor = '#f0f9ff'
  }
}

const handleDrop = (event: DragEvent, dropIndex: number) => {
  event.preventDefault()
  if (dragIndex.value === null || dragIndex.value === dropIndex) {
    return
  }
  
  // 重新排序列（使用orderedColumns的当前值）
  const currentColumns = [...orderedColumns.value]
  const [removed] = currentColumns.splice(dragIndex.value, 1)
  currentColumns.splice(dropIndex, 0, removed)
  
  // 更新列顺序
  columnOrder.value = currentColumns.map(col => col.prop)
  
  // 清除样式
  const items = columnListRef.value?.querySelectorAll('.column-item')
  items?.forEach((item) => {
    (item as HTMLElement).style.backgroundColor = ''
  })
}

const handleDragEnd = () => {
  dragIndex.value = null
  // 清除所有拖拽样式
  const items = columnListRef.value?.querySelectorAll('.column-item')
  items?.forEach((item) => {
    const el = item as HTMLElement
    el.style.opacity = ''
    el.style.backgroundColor = ''
  })
}

// 保存列顺序
const handleSaveColumnOrder = () => {
  // 列顺序已经实时更新，这里只需要关闭弹窗
  showColumnSettings.value = false
  ElMessage.success('列顺序已保存')
}

// 列宽调整处理函数
const handleResizeStart = (event: MouseEvent, prop: string) => {
  event.preventDefault()
  event.stopPropagation()
  
  resizingColumn.value = prop
  resizeStartX.value = event.clientX
  
  // 获取当前列宽
  const currentWidth = columnWidths[prop] || columnConfig.value.find(c => c.prop === prop)?.width
  resizeStartWidth.value = currentWidth || 120
  
  // 添加全局事件监听
  document.addEventListener('mousemove', handleResizeMove)
  document.addEventListener('mouseup', handleResizeEnd)
  
  // 添加样式
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const handleResizeMove = (event: MouseEvent) => {
  if (!resizingColumn.value) return
  
  const diff = event.clientX - resizeStartX.value
  const newWidth = Math.max(120, resizeStartWidth.value + diff) // 最小宽度120
  
  columnWidths[resizingColumn.value] = newWidth
}

const handleResizeEnd = () => {
  if (resizingColumn.value) {
    resizingColumn.value = null
  }
  
  // 移除全局事件监听
  document.removeEventListener('mousemove', handleResizeMove)
  document.removeEventListener('mouseup', handleResizeEnd)
  
  // 恢复样式
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

// 双击重置列宽为默认值
const handleResizeAuto = (prop: string) => {
  // 移除自定义宽度，恢复为配置的默认宽度
  delete columnWidths[prop]
  ElMessage.success('列宽已重置为默认值')
}

// 计算列宽，确保表格总宽度填满屏幕
const getColumnWidth = (col: ColumnConfig): number | undefined => {
  // 如果设置了自定义宽度，使用自定义宽度
  if (columnWidths[col.prop]) {
    return columnWidths[col.prop]
  }
  // 如果配置中有固定宽度，使用配置的宽度
  if (col.width) {
    return col.width
  }
  // 否则使用最小宽度
  return col.minWidth || 120
}

// 获取排序图标
const getSortIcon = (prop: string) => {
  if (sortInfo.prop === prop) {
    return sortInfo.order === 'ascending' ? ArrowUp : ArrowDown
  }
  return Sort
}

// 获取排序图标颜色
const getSortIconColor = (prop: string) => {
  if (sortInfo.prop === prop) {
    return '#409eff' // 激活状态使用主题色
  }
  return '#c0c4cc' // 未激活状态使用灰色
}

// 处理列头排序点击
const handleHeaderSortClick = (prop: string) => {
  // 计算下一个排序状态：无排序 -> 升序 -> 降序 -> 无排序
  if (sortInfo.prop === prop) {
    if (sortInfo.order === 'ascending') {
      sortInfo.order = 'descending'
    } else if (sortInfo.order === 'descending') {
      sortInfo.prop = undefined
      sortInfo.order = undefined
    }
  } else {
    sortInfo.prop = prop
    sortInfo.order = 'ascending'
  }
  
  pagination.page = 1
  loadData(false)
}

// 检查是否有激活的筛选条件
const hasActiveFilter = (prop: string) => {
  // 查找对应的列配置
  const col = columnConfig.value.find(c => c.prop === prop)
  if (!col || !col.filterable) return false
  
  switch (col.filterType) {
    case 'number':
      if (prop === 'id') {
        // 单条件
        return !!(filterForm[`${prop}Operator`] && filterForm[`${prop}Value`] !== undefined)
      } else {
        // 多条件
        const filters = filterForm[`${prop}Filters`]
        return Array.isArray(filters) && filters.some((f: any) => f && f.operator && f.value !== undefined)
      }
    case 'multi-select':
      const multiValue = filterForm[prop]
      return Array.isArray(multiValue) && multiValue.length > 0
    case 'text':
    case 'date':
    case 'select':
      return !!filterForm[prop]
    default:
      return false
  }
}

// 获取筛选选项
const getFilterOptions = (prop: string): string[] => {
  // 优先从 filterOptions 获取（从后端加载的）
  if (filterOptions[prop] && filterOptions[prop].length > 0) {
    return filterOptions[prop]
  }
  // 其次从列配置的 options 获取
  const col = columnConfig.value.find(c => c.prop === prop)
  if (col && col.options) {
    return col.options
  }
  return []
}

// 刷新筛选选项（从后端获取最新的筛选选项）
const refreshFilterOptions = async () => {
  try {
    const options = await dataApi.getFilterOptions()
    // 更新 filterOptions
    Object.keys(options).forEach(prop => {
      filterOptions[prop] = options[prop]
    })
  } catch (error) {
    console.error('[筛选选项] 刷新筛选选项失败:', error)
    // 失败时不影响主流程，使用列配置中的 options
  }
}

// 获取筛选弹窗宽度
const getFilterPopoverWidth = (filterType: string): number => {
  switch (filterType) {
    case 'number':
      return 320
    case 'multi-select':
    case 'select':
      return 250
    case 'text':
    case 'date':
      return 250
    default:
      return 250
  }
}

// 加载统计信息
const loadStatistics = async () => {
  statisticsLoading.value = true
  try {
    const data = await dataApi.getStatistics()
    statisticsData.value = data
  } catch (error: any) {
    const errorMsg = error?.message || '加载统计信息失败'
    ElMessage.error(errorMsg)
  } finally {
    statisticsLoading.value = false
  }
}

// 打开统计弹窗
const handleShowStatistics = () => {
  showStatisticsDialog.value = true
  loadStatistics()
}

// 强制启用分页跳转输入框（移除禁用状态）
const enablePaginationJumper = () => {
  nextTick(() => {
    // 查找分页跳转输入框并移除禁用状态
    const jumpInputs = document.querySelectorAll('.el-pagination__jump input')
    jumpInputs.forEach((input: any) => {
      if (input) {
        input.removeAttribute('disabled')
        input.disabled = false
        // 移除父元素的禁用类
        const inputWrapper = input.closest('.el-input')
        if (inputWrapper) {
          inputWrapper.classList.remove('is-disabled')
          // 移除 wrapper 上的禁用类
          const wrapper = inputWrapper.querySelector('.el-input__wrapper')
          if (wrapper) {
            wrapper.classList.remove('is-disabled')
          }
        }
      }
    })
  })
  
  // 延迟再次检查，确保 Element Plus 的更新不会覆盖我们的设置
  setTimeout(() => {
    nextTick(() => {
      const jumpInputs = document.querySelectorAll('.el-pagination__jump input')
      jumpInputs.forEach((input: any) => {
        if (input) {
          input.removeAttribute('disabled')
          input.disabled = false
          const inputWrapper = input.closest('.el-input')
          if (inputWrapper) {
            inputWrapper.classList.remove('is-disabled')
          }
        }
      })
    })
  }, 100)
}

// 初始化表格宽度，确保填满屏幕
const initTableWidth = () => {
  nextTick(() => {
    if (!tableRef.value) return
    
    const tableEl = tableRef.value.$el as HTMLElement
    if (!tableEl) return
    
    const tableContainer = tableEl.closest('.table-container') as HTMLElement
    if (!tableContainer) return
    
    const containerWidth = tableContainer.clientWidth
    if (containerWidth <= 0) return
    
    // 计算可见列（不包括固定列）
    const visibleCols = orderedColumns.value.filter(col => columnVisible[col.prop] && !col.fixed)
    if (visibleCols.length === 0) return
    
    // 计算已设置的列宽总和
    // 展开列固定50px
    let totalWidth = 50
    // 计算所有可见列的宽度（包括固定列）
    orderedColumns.value.forEach(col => {
      if (columnVisible[col.prop]) {
        const width = getColumnWidth(col)
        if (width) {
          totalWidth += width
        }
      }
    })
    
    // 如果总宽度小于容器宽度，调整最后一列（非固定列）的宽度
    if (totalWidth < containerWidth && visibleCols.length > 0) {
      const lastCol = visibleCols[visibleCols.length - 1]
      const lastColWidth = getColumnWidth(lastCol) || 120
      const newWidth = lastColWidth + (containerWidth - totalWidth)
      columnWidths[lastCol.prop] = Math.max(newWidth, lastCol.minWidth || 120)
    }
  })
}

// 暴露方法给父组件
const exposedMethods = {
  refreshData: async () => {
    await loadData(false, true) // Silent refresh
    await refreshFilterOptions()
  },
  refreshColumns: loadColumnsConfig
}

defineExpose(exposedMethods)

// 注册到全局注册表的函数 (Removed as App.vue handles this)
/*
const registerToGlobalRegistry = () => {
  // 等待一下确保 DOM 完全渲染
  const root = document.getElementById('root')
  const tableId = root?.dataset.tableId
  
  if (tableId) {
    // 注册到全局注册表
    if (!(window as any).__nice_table_registry) {
      (window as any).__nice_table_registry = {}
    }
    
    const registry = (window as any).__nice_table_registry
    registry[tableId] = exposedMethods
    console.log('DataTable: NiceTable instance registered:', tableId, registry)
    
    // 触发自定义事件
    window.dispatchEvent(new CustomEvent('nice-table-ready', { detail: { tableId } }))
    return true
  }
  return false
}
*/

// 初始化
onMounted(async () => {
  try {
    await loadColumnsConfig()  // 先加载列配置，确保列可见性已初始化
    // 确保列配置加载完成后再加载数据
    await loadData()
    // 初始化表格宽度
    initTableWidth()
  } catch (error) {
    // 即使列配置加载失败，也尝试加载数据（使用默认配置）
    if (columnConfig.value.length === 0) {
      columnConfig.value = defaultColumns
      initColumnVisible(defaultColumns)
      initFilterForm(defaultColumns)
    }
    await loadData()
    // 初始化表格宽度
    initTableWidth()
  }
  
  // 等待多个 tick 后注册到全局注册表
  await nextTick()
  await nextTick()
  // await new Promise(resolve => setTimeout(resolve, 300)) // 额外等待 300ms 确保 DOM 完全渲染
  
  // 强制启用分页跳转输入框
  enablePaginationJumper()
  
  /*
  // 如果第一次尝试失败，使用轮询重试
  if (!registerToGlobalRegistry()) {
    let retries = 0
    const maxRetries = 30 // 增加到 30 次，总共 6 秒
    const interval = setInterval(() => {
      retries++
      if (registerToGlobalRegistry() || retries >= maxRetries) {
        clearInterval(interval)
        if (retries >= maxRetries) {
          console.warn('DataTable: Failed to register to global registry after', maxRetries, 'retries')
          // 最后一次尝试：直接检查 root元素
          const root = document.getElementById('root')
          const tableId = root?.dataset.tableId
          if (tableId && !(window as any).__nice_table_registry?.[tableId]) {
            console.error('DataTable: Registration failed. Root element:', root, 'TableId:', tableId)
          }
        }
      }
    }, 200)
  }
  */
})
</script>

<style scoped>
.table-card {
  margin: 0;
  height: 100%; /* Parent container control */
  width: 100%;
  max-width: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

:deep(.el-card__body) {
  padding: 16px;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 表格容器：占据剩余空间 */
.table-container {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative; /* 用于进度条定位 */
}

/* 列头样式 */
.column-header {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.column-header > span {
  font-weight: 600;
  margin-bottom: 4px;
}

/* 标题行样式（包含筛选图标、标题和排序图标） */
.header-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.header-title-row > span {
  font-weight: 600;
  margin-bottom: 0;
  flex: 1;
  text-align: center;
}

/* 筛选图标样式（左侧） */
.filter-icon {
  cursor: pointer;
  font-size: 14px;
  transition: color 0.2s;
  flex-shrink: 0;
}

.filter-icon:hover {
  color: #409eff !important;
}

/* 排序图标样式（右侧） */
.sort-icon {
  cursor: pointer;
  font-size: 14px;
  transition: color 0.2s;
  flex-shrink: 0;
  margin-left: auto;
}

.sort-icon:hover {
  color: #409eff !important;
}

/* 筛选悬浮框样式 */
.filter-popover {
  padding: 4px 0;
}

.filter-popover .filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 隐藏 Element Plus 默认的排序图标 */
:deep(.el-table .caret-wrapper) {
  display: none !important;
}

:deep(.el-table .sort-caret) {
  display: none !important;
}

/* 防止筛选下拉菜单关闭 popover */
:deep(.filter-select-dropdown) {
  pointer-events: auto !important;
}

:deep(.filter-select-dropdown *) {
  pointer-events: auto !important;
}

/* 保持多选筛选的 popover 打开 */
:deep(.filter-select-dropdown-keep-open) {
  pointer-events: auto !important;
}

:deep(.filter-select-dropdown-keep-open *) {
  pointer-events: auto !important;
}

/* 防止多选下拉框关闭时触发 popover 关闭 */
:deep(.el-select-dropdown) {
  pointer-events: auto !important;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 选中行样式 - 更明显的颜色（更深） */
:deep(.selected-row) {
  background-color: #7ab8ff !important;
  border-left: 3px solid #409eff !important;
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.3) !important;
}

:deep(.selected-row:hover) {
  background-color: #66b1ff !important;
  border-left-color: #66b1ff !important;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.4) !important;
}

:deep(.el-table__row.selected-row) {
  cursor: pointer;
  font-weight: 500;
}

/* Element Plus 的 highlight-current-row 样式增强 */
:deep(.el-table__row.current-row) {
  background-color: #7ab8ff !important;
  border-left: 3px solid #409eff !important;
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.3) !important;
}

:deep(.el-table__row.current-row:hover) {
  background-color: #66b1ff !important;
  border-left-color: #66b1ff !important;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.4) !important;
}

/* 展开详情样式 */
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

.error-message {
  color: #f56c6c;
}

/* 详情表格样式 */
.expand-detail :deep(.el-table) {
  background-color: transparent;
}

.expand-detail :deep(.el-table__header) {
  background-color: #fafafa;
}

.expand-detail :deep(.el-table th) {
  background-color: #fafafa;
  font-weight: 600;
  color: #303133;
}

.expand-detail :deep(.el-table tr) {
  background-color: #fff;
}

.expand-detail :deep(.el-table tr:hover) {
  background-color: #f5f7fa;
}

.detail-item {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid #e4e7ed;
  align-items: center;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item:hover {
  background-color: #fafafa;
  padding-left: 8px;
  padding-right: 8px;
  margin-left: -8px;
  margin-right: -8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.detail-label {
  font-weight: 600;
  color: #606266;
  min-width: 100px;
  margin-right: 16px;
  font-size: 14px;
}

.detail-value {
  color: #303133;
  flex: 1;
  font-size: 14px;
}

/* 自定义展开图标样式 */
:deep(.el-table__expand-icon) {
  font-size: 16px;
  color: #409eff;
  font-weight: bold;
}

:deep(.el-table__expand-icon--expanded) {
  transform: rotate(45deg);
}

/* 列设置下拉菜单样式 */
:deep(.el-dropdown-menu__item) {
  padding: 8px 20px;
  cursor: default;
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: transparent;
}

:deep(.el-dropdown-menu__item .el-checkbox) {
  width: 100%;
  cursor: pointer;
}

:deep(.el-dropdown-menu__item .el-checkbox__label) {
  cursor: pointer;
  padding-left: 8px;
}

/* 表格单元格内容不换行，保持单行显示 */
:deep(.el-table .el-table__cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.el-table .el-table__body-wrapper .el-table__cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.el-table .el-table__header-wrapper .el-table__cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 使用固定表格布局，列宽由 width 属性控制，不支持自动调整 */
:deep(.el-table) {
  table-layout: fixed !important;
}

:deep(.el-table__header-wrapper),
:deep(.el-table__body-wrapper) {
  width: 100%;
}

/* 确保单元格内容不换行 */
:deep(.el-table td),
:deep(.el-table th) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 展开详情表格也保持单行 */
.expand-detail :deep(.el-table .el-table__cell) {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 列设置弹窗样式 */
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
  cursor: move;
  transition: all 0.2s;
  user-select: none;
}

.column-item:hover {
  background-color: #f5f7fa;
  border-color: #c0c4cc;
}

.column-item.dragging {
  opacity: 0.5;
}

.column-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drag-handle {
  color: #909399;
  cursor: grab;
  font-size: 16px;
  transition: color 0.2s;
}

.drag-handle:hover {
  color: #409eff;
}

.drag-handle:active {
  cursor: grabbing;
}

.drag-handle.dragging {
  color: #409eff;
}

/* 列宽调整手柄样式 */
.column-resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 4px;
  height: 100%;
  cursor: col-resize;
  background-color: transparent;
  z-index: 10;
  transition: background-color 0.2s;
}

.column-resize-handle:hover {
  background-color: #409eff;
}

/* 确保列头容器有相对定位，以便调整手柄正确定位 */
:deep(.el-table__header-wrapper .el-table__cell) {
  position: relative;
}

:deep(.el-table__header-wrapper .column-header) {
  position: relative;
  padding-right: 8px;
  width: 100%;
  height: 100%;
}

/* bytes类型字段显示样式 */
.bytes-display {
  font-family: 'Courier New', 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  color: #409eff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  display: inline-block;
  cursor: help;
}

/* 添加数据对话框样式 */
.add-data-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 8px 0;
}

.add-data-content .el-form-item {
  margin-bottom: 16px;
}

/* 统计信息弹窗样式 */
.statistics-content {
  min-height: 150px;
}

.statistics-content :deep(.el-table) {
  border-radius: 4px;
}

.statistics-content :deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
}

/* 静默加载进度条 */
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
  pointer-events: none;
}

@keyframes loading-bar {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* 表格过渡动画 */
.table-with-transition {
  transition: opacity 0.2s ease-in-out;
}

.table-with-transition :deep(.el-table__body-wrapper) {
  transition: opacity 0.2s ease-in-out;
}

/* 优化加载遮罩样式，减少白屏感 */
:deep(.el-loading-mask) {
  background-color: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(2px);
}

/* 表格行淡入动画 */
:deep(.el-table__row) {
  animation: fadeInRow 0.3s ease-in;
}

@keyframes fadeInRow {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 减小表格行高，让每页显示更多行 */
:deep(.el-table .el-table__body .el-table__cell) {
  padding: 4px 0 !important;
  line-height: 1.1 !important;
}

:deep(.el-table .el-table__header .el-table__cell) {
  padding: 6px 0 !important;
  line-height: 1.1 !important;
}

/* 减小表格单元格内容的内边距 */
:deep(.el-table .cell) {
  padding: 0 8px;
  line-height: 1.1;
  font-size: 13px;
}

/* 减小表头字体大小和内边距 */
:deep(.el-table th.el-table__cell .cell) {
  font-size: 13px;
  font-weight: 600;
  padding: 0 8px;
}

/* Hide spin buttons for number input in pagination jumper */
:deep(.el-pagination__jump input[type=number]::-webkit-inner-spin-button),
:deep(.el-pagination__jump input[type=number]::-webkit-outer-spin-button) {
  -webkit-appearance: none;
  margin: 0;
}
:deep(.el-pagination__jump input[type=number]) {
  -moz-appearance: textfield;
}

/* 分页跳转输入框：移除禁用状态，设置正确的样式和光标 */
:deep(.el-pagination__jump) {
  cursor: pointer !important;
}

:deep(.el-pagination__jump *) {
  cursor: pointer !important;
}

:deep(.el-pagination__jump .el-input) {
  cursor: pointer !important;
}

:deep(.el-pagination__jump .el-input__inner) {
  cursor: pointer !important;
  color: #303133 !important;
  background-color: #fff !important;
  opacity: 1 !important;
}

:deep(.el-pagination__jump .el-input__inner:disabled),
:deep(.el-pagination__jump .el-input__inner[disabled]) {
  cursor: pointer !important;
  color: #303133 !important;
  background-color: #fff !important;
  -webkit-text-fill-color: #303133 !important;
  opacity: 1 !important;
}

:deep(.el-pagination__jump .el-input__wrapper) {
  cursor: pointer !important;
}

:deep(.el-pagination__jump input) {
  cursor: pointer !important;
  color: #303133 !important;
  background-color: #fff !important;
  opacity: 1 !important;
}

:deep(.el-pagination__jump input:disabled),
:deep(.el-pagination__jump input[disabled]) {
  cursor: pointer !important;
  color: #303133 !important;
  background-color: #fff !important;
  -webkit-text-fill-color: #303133 !important;
  opacity: 1 !important;
}

/* 移除禁用状态的样式 */
:deep(.el-pagination__jump .el-input.is-disabled),
:deep(.el-pagination__jump .el-input.is-disabled *) {
  cursor: pointer !important;
}

:deep(.el-pagination__jump .el-input.is-disabled .el-input__inner) {
  cursor: pointer !important;
  color: #303133 !important;
  background-color: #fff !important;
  -webkit-text-fill-color: #303133 !important;
  opacity: 1 !important;
}

/* 覆盖 Element Plus 的禁用状态样式 */
:deep(.el-pagination__jump .el-input.is-disabled .el-input__wrapper) {
  cursor: pointer !important;
  background-color: #fff !important;
  box-shadow: 0 0 0 1px #dcdfe6 inset !important;
}

:deep(.el-pagination__jump .el-input.is-disabled .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #409eff inset !important;
}

</style>
