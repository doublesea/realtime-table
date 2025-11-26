<template>
  <el-card class="table-card" :body-style="{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }">
    <!-- 工具栏 -->
    <div class="toolbar" style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
      <div>
        <el-button :icon="Setting" size="small" @click="showColumnSettings = true">
          列设置
        </el-button>
      </div>
      <div>
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

    <!-- 分页 -->
    <div class="pagination-container" style="flex-shrink: 0; margin-top: 16px;">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :page-sizes="[50, 100, 200, 500]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        style="justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 添加数据弹窗 -->
    <el-dialog
      v-model="showAddDataDialog"
      title="添加数据"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="add-data-content">
        <el-form :model="newDataForm" label-width="120px" ref="newDataFormRef">
          <el-form-item
            v-for="col in orderedColumns"
            :key="col.prop"
            :label="col.label"
            :prop="col.prop"
          >
            <el-input
              v-if="col.type === 'string' || (col.filterType === 'text' && col.type !== 'number' && col.type !== 'date' && col.type !== 'bytes')"
              v-model="newDataForm[col.prop]"
              :placeholder="`请输入${col.label}`"
              clearable
            />
            <el-input-number
              v-else-if="col.type === 'number'"
              v-model="newDataForm[col.prop]"
              :placeholder="`请输入${col.label}`"
              style="width: 100%"
            />
            <el-date-picker
              v-else-if="col.type === 'date' && col.prop !== 'ts'"
              v-model="newDataForm[col.prop]"
              type="date"
              :placeholder="`请选择${col.label}`"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
            <el-input
              v-else-if="col.prop === 'ts'"
              v-model="newDataForm[col.prop]"
              :placeholder="'格式: YYYY-MM-DD HH:MM:SS.ffffff 或 YYYY-MM-DD'"
              clearable
            />
            <el-input
              v-else-if="col.type === 'bytes'"
              v-model="newDataForm[col.prop]"
              :placeholder="'16进制格式，如: FF 00 1A'"
              clearable
            />
            <el-select
              v-else-if="col.filterType === 'multi-select' || col.filterType === 'select'"
              v-model="newDataForm[col.prop]"
              :placeholder="`请选择${col.label}`"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="option in getFilterOptions(col.prop)"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
            <el-input
              v-else
              v-model="newDataForm[col.prop]"
              :placeholder="`请输入${col.label}`"
              clearable
            />
          </el-form-item>
        </el-form>
        <div style="margin-top: 16px; color: #909399; font-size: 12px;">
          <p>提示：</p>
          <ul style="margin: 8px 0; padding-left: 20px;">
            <li>ID字段会自动生成，无需填写</li>
            <li>如果字段为空，将使用默认值或留空</li>
            <li>时间戳字段(ts)支持日期时间格式</li>
            <li>Bytes类型字段支持16进制格式（如: FF 00 1A）</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAddDataDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddData" :loading="addingData">确定</el-button>
      </template>
    </el-dialog>

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
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Delete, Setting, ArrowDown, ArrowUp, Sort, Filter, Rank } from '@element-plus/icons-vue'
import { TableData, FilterParams, NumberFilter, RowDetail, ColumnConfig } from '../types'
import { dataApi } from '../api/data'
import type { ElTable } from 'element-plus'
import type { FormInstance } from 'element-plus'

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

// 添加数据相关状态
const showAddDataDialog = ref(false)
const addingData = ref(false)
const newDataForm = reactive<Record<string, any>>({})
const newDataFormRef = ref<FormInstance>()

// 自动添加数据相关状态
const autoAddRunning = ref(false)
const autoAddLoading = ref(false)

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
    
    // 调试信息：如果是静默刷新，输出日志
    if (silent) {
      console.log(`[自动刷新] 总数据: ${pagination.total}, 当前页: ${pagination.page}/${Math.ceil(pagination.total / pagination.pageSize)}, 当前页数据量: ${tableData.value.length}`)
    }
    
    // 数据加载完成后
    await nextTick()
    
    // 如果是静默刷新（自动刷新），跳转到最后一页并选中最后一行
    if (silent) {
      // 计算总页数
      const totalPages = Math.ceil(pagination.total / pagination.pageSize)
      console.log(`[自动刷新] 计算总页数: ${totalPages}, 当前页: ${pagination.page}, 总数据: ${pagination.total}, 每页: ${pagination.pageSize}`)
      
      if (totalPages > 0 && pagination.page !== totalPages) {
        // 如果不在最后一页，跳转到最后一页并重新加载
        console.log(`[自动刷新] 跳转到最后一页: ${totalPages}`)
        pagination.page = totalPages
        // 重新请求最后一页的数据
        const lastPageResponse = await dataApi.getList({
          page: totalPages,
          pageSize: pagination.pageSize,
          filters: requestFilters,
          sortBy: sortBy,
          sortOrder: sortOrder
        })
        tableData.value = lastPageResponse.list
        pagination.total = lastPageResponse.total
        pagination.page = lastPageResponse.page
        pagination.pageSize = lastPageResponse.pageSize
        
        console.log(`[自动刷新] 最后一页数据加载完成，数据量: ${tableData.value.length}`)
        
        // 选中最后一行
        await nextTick()
        if (tableData.value.length > 0) {
          const lastRow = tableData.value[tableData.value.length - 1]
          console.log(`[自动刷新] 选中最后一行，ID: ${lastRow.id}`)
          selectedRowId.value = lastRow.id
          if (tableRef.value) {
            tableRef.value.setCurrentRow(lastRow)
          }
          setTimeout(() => {
            scrollToLastRow()
          }, 100)
        }
        return
      }
      // 已经在最后一页，选中最后一行
      if (tableData.value.length > 0) {
        const lastRow = tableData.value[tableData.value.length - 1]
        console.log(`[自动刷新] 已在最后一页，选中最后一行，ID: ${lastRow.id}`)
        selectedRowId.value = lastRow.id
        if (tableRef.value) {
          tableRef.value.setCurrentRow(lastRow)
        }
        setTimeout(() => {
          scrollToLastRow()
        }, 100)
      }
    } else if (selectedRowId.value !== null && shouldKeepSelected) {
      // 如果选中了行且需要保持选中状态，恢复选中状态
      // 查找选中行在当前页数据中的位置
      const selectedRow = tableData.value.find(row => row.id === selectedRowId.value)
      if (selectedRow) {
        // 设置表格的当前行，触发 highlight-current-row 高亮
        if (tableRef.value) {
          tableRef.value.setCurrentRow(selectedRow)
        }
        // 使用setTimeout确保DOM完全渲染后再滚动
        setTimeout(() => {
          scrollToSelectedRow()
        }, 100)
      } else {
        // 如果选中行不在当前页，但仍然在筛选结果中（已跳转到对应页面），尝试再次查找
        // 延迟一点时间，确保表格已完全渲染
        setTimeout(() => {
          const row = tableData.value.find(r => r.id === selectedRowId.value)
          if (row && tableRef.value) {
            tableRef.value.setCurrentRow(row)
            scrollToSelectedRow()
          }
        }, 150)
      }
    }
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '加载数据失败'
    ElMessage.error(`加载数据失败: ${errorMsg}`)
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
      allKeys.add(key)
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
  pagination.page = 1
  selectedRowId.value = null // 重置时清除选中状态
  loadData(false)
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
    console.log('[筛选选项] 已刷新筛选选项:', options)
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

// 处理添加数据
const handleAddData = async () => {
  if (!newDataFormRef.value) return
  
  // 验证表单
  try {
    await newDataFormRef.value.validate()
  } catch (error) {
    return
  }
  
  addingData.value = true
  try {
    // 准备新数据，移除空值（除了允许为空的字段）
    const dataToAdd: Record<string, any> = {}
    orderedColumns.value.forEach(col => {
      const value = newDataForm[col.prop]
      // ID字段不包含在提交数据中（会自动生成）
      if (col.prop === 'id') {
        return
      }
      // 如果值不为空，添加到提交数据中
      if (value !== undefined && value !== null && value !== '') {
        dataToAdd[col.prop] = value
      }
    })
    
    // 调用API添加数据
    const result = await dataApi.addData(dataToAdd)
    
    ElMessage.success(`成功添加 ${result.added_count} 条数据`)
    
    // 如果有新字段，重新加载列配置
    if (result.columns_updated && result.added_columns.length > 0) {
      ElMessage.info(`检测到新字段: ${result.added_columns.join(', ')}，正在更新列配置...`)
      await loadColumnsConfig()
      // 重新初始化筛选表单
      initFilterForm(columnConfig.value)
    }
    
    // 关闭对话框
    showAddDataDialog.value = false
    
    // 清空表单
    Object.keys(newDataForm).forEach(key => {
      delete newDataForm[key]
    })
    
    // 刷新数据（保持当前筛选条件和分页）
    await loadData(false)
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '添加数据失败'
    ElMessage.error(`添加数据失败: ${errorMsg}`)
  } finally {
    addingData.value = false
  }
}

// 监听添加数据对话框打开，初始化表单
const initAddDataForm = () => {
  // 清空现有表单数据
  Object.keys(newDataForm).forEach(key => {
    delete newDataForm[key]
  })
  
  // 根据列配置初始化表单
  orderedColumns.value.forEach(col => {
    // ID字段不显示在表单中（会自动生成）
    if (col.prop === 'id') {
      return
    }
    // 根据字段类型设置默认值
    if (col.type === 'number') {
      newDataForm[col.prop] = undefined
    } else if (col.filterType === 'multi-select') {
      newDataForm[col.prop] = []
    } else {
      newDataForm[col.prop] = undefined
    }
  })
}

// 监听对话框显示状态
watch(showAddDataDialog, (newVal) => {
  if (newVal) {
    initAddDataForm()
  }
})

// 处理自动添加数据
const handleToggleAutoAdd = async () => {
  autoAddLoading.value = true
  try {
    if (autoAddRunning.value) {
      // 停止自动添加
      await dataApi.stopAutoAdd()
      autoAddRunning.value = false
      
      // 立即清除自动刷新定时器
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer)
        autoRefreshTimer = null
        console.log('[停止] 已清除自动刷新定时器')
      }
      
      // 重置静默加载状态
      silentLoading.value = false
      
      // 重新启动状态检查定时器（以便检测下次启动）
      startStatusCheck()
      
      ElMessage.success('已停止自动添加数据')
    } else {
      // 启动自动添加（每0.5秒添加5条数据）
      await dataApi.startAutoAdd(5, 0.5)
      autoAddRunning.value = true
      ElMessage.success('已启动自动添加数据（每0.5秒添加5条）')
      
      // 启动定时刷新（会立即执行一次刷新，然后每0.5秒刷新一次）
      startAutoRefresh()
    }
  } catch (error: any) {
    const errorMsg = error?.message || '操作失败'
    ElMessage.error(`操作失败: ${errorMsg}`)
  } finally {
    autoAddLoading.value = false
  }
}

// 自动刷新定时器
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null

const startAutoRefresh = () => {
  // 清除旧的定时器
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    console.log('[自动刷新] 清除旧的定时器')
  }
  
  console.log('[自动刷新] 启动自动刷新定时器（每0.5秒刷新一次）')
  
  // 立即执行一次刷新，不等待定时器
  const performRefresh = async () => {
    if (!autoAddRunning.value) {
      return
    }
    console.log('[自动刷新] 立即刷新数据...')
    try {
        await loadData(false, true) // 不保持选中行，使用静默模式
        // 刷新筛选选项
        await refreshFilterOptions()
        console.log('[自动刷新] 数据刷新完成')
    } catch (error) {
      console.error('[自动刷新] 刷新失败:', error)
    }
  }
  
  // 立即执行一次刷新
  performRefresh()
  
  // 每0.5秒刷新一次数据（使用静默模式，不显示遮罩），与数据添加频率同步
  autoRefreshTimer = setInterval(async () => {
    // 每次刷新前先检查自动添加状态（因为可能在Python侧启动）
    let shouldContinue = false
    try {
      const status = await dataApi.getAutoAddStatus()
      const wasRunning = autoAddRunning.value
      autoAddRunning.value = status.running
      
      // 如果状态从停止变为运行，记录日志
      if (!wasRunning && status.running) {
        console.log('[自动刷新] 检测到自动添加已启动')
      }
      
      // 如果状态已停止，立即清除定时器并返回
      if (!status.running) {
        console.log('[自动刷新] 检测到自动添加已停止，立即清除定时器')
        if (autoRefreshTimer) {
          clearInterval(autoRefreshTimer)
          autoRefreshTimer = null
        }
        // 重置静默加载状态
        silentLoading.value = false
        // 重新启动状态检查定时器（以便检测下次启动）
        startStatusCheck()
        return // 立即返回，不再执行后续刷新
      }
      
      shouldContinue = true
    } catch (error) {
      console.error('[自动刷新] 检查状态失败:', error)
      // 如果检查失败，但当前状态显示运行中，继续刷新（避免网络问题导致停止）
      shouldContinue = autoAddRunning.value
    }
    
    // 只有在确认运行中时才刷新
    if (shouldContinue && autoAddRunning.value) {
      // 静默刷新，自动跳转到最后一页并选中最后一行
      console.log('[自动刷新] 开始刷新数据... (autoAddRunning:', autoAddRunning.value, ')')
      try {
        await loadData(false, true) // 不保持选中行，使用静默模式
        // 刷新筛选选项
        await refreshFilterOptions()
        console.log('[自动刷新] 数据刷新完成')
      } catch (error) {
        console.error('[自动刷新] 刷新失败:', error)
      }
    }
  }, 500) // 每0.5秒刷新一次，与数据添加频率同步
}

// 检查自动添加状态
const checkAutoAddStatus = async () => {
  try {
    console.log('[初始化] 检查自动添加状态...')
    const status = await dataApi.getAutoAddStatus()
    console.log('[初始化] 自动添加状态:', status)
    autoAddRunning.value = status.running
    if (status.running) {
      console.log('[初始化] 自动添加正在运行，启动自动刷新')
      startAutoRefresh()
      // 不需要启动状态检查，因为自动刷新定时器会检查状态
    } else {
      console.log('[初始化] 自动添加未运行 - 请在NiceGUI页面点击"开始自动添加"按钮启动')
      // 只在未运行时启动状态检查定时器
    }
  } catch (error) {
    console.error('[初始化] 检查自动添加状态失败:', error)
    // 忽略错误，不影响主流程
  }
}

// 定期检查自动添加状态的定时器
let statusCheckTimer: ReturnType<typeof setInterval> | null = null

const startStatusCheck = () => {
  // 清除旧的定时器
  if (statusCheckTimer) {
    clearInterval(statusCheckTimer)
    statusCheckTimer = null
  }
  
  // 只在自动添加未运行时才启动状态检查定时器
  // 如果已经在运行，则不需要状态检查（因为自动刷新定时器会检查状态）
  if (autoAddRunning.value) {
    console.log('[状态检查] 自动添加已在运行，无需启动状态检查定时器')
    return
  }
  
  console.log('[状态检查] 启动状态检查定时器（每0.5秒检查一次，仅在未运行时检查）')
  
  // 每0.5秒检查一次自动添加状态（因为可能在Python侧启动），缩短检测延迟
  statusCheckTimer = setInterval(async () => {
    // 如果自动添加已经在运行，停止状态检查（自动刷新定时器会接管）
    if (autoAddRunning.value) {
      console.log('[状态检查] 自动添加已在运行，停止状态检查定时器')
      if (statusCheckTimer) {
        clearInterval(statusCheckTimer)
        statusCheckTimer = null
      }
      return
    }
    
    try {
      const status = await dataApi.getAutoAddStatus()
      const wasRunning = autoAddRunning.value
      autoAddRunning.value = status.running
      
      // 如果状态从停止变为运行，启动自动刷新并停止状态检查
      if (!wasRunning && status.running) {
        console.log('[状态检查] 检测到自动添加已启动，立即开始自动刷新并停止状态检查')
        // 停止状态检查定时器（自动刷新定时器会接管状态检查）
        if (statusCheckTimer) {
          clearInterval(statusCheckTimer)
          statusCheckTimer = null
        }
        startAutoRefresh() // startAutoRefresh 内部会立即执行一次刷新
      }
    } catch (error) {
      console.error('[状态检查] 检查状态失败:', error)
      // 忽略错误，不影响主流程
    }
  }, 500) // 每0.5秒检查一次状态（只在未运行时），缩短检测延迟
}

const stopStatusCheck = () => {
  if (statusCheckTimer) {
    clearInterval(statusCheckTimer)
    statusCheckTimer = null
    console.log('[状态检查] 已停止状态检查定时器')
  }
}

// 初始化
onMounted(async () => {
  try {
    await loadColumnsConfig()  // 先加载列配置，确保列可见性已初始化
    // 确保列配置加载完成后再加载数据
    await loadData()
    // 初始化表格宽度
    initTableWidth()
    // 检查自动添加状态
    await checkAutoAddStatus()
    // 启动定期状态检查
    startStatusCheck()
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
    // 检查自动添加状态（内部会根据状态决定是否启动状态检查）
    await checkAutoAddStatus()
    // 只在未运行时启动状态检查（checkAutoAddStatus 内部已处理）
    if (!autoAddRunning.value) {
      startStatusCheck()
    }
  }
})

// 组件卸载时清理定时器
onUnmounted(() => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
  if (statusCheckTimer) {
    clearInterval(statusCheckTimer)
    statusCheckTimer = null
  }
})
</script>

<style scoped>
.table-card {
  margin: 0;
  height: 100vh;
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

/* 选中行样式 */
:deep(.selected-row) {
  background-color: #ecf5ff !important;
}

:deep(.selected-row:hover) {
  background-color: #d4e8ff !important;
}

:deep(.el-table__row.selected-row) {
  cursor: pointer;
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

</style>


