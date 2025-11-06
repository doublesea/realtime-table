<template>
  <el-card class="table-card" :body-style="{ padding: '16px' }">
    <!-- 工具栏 -->
    <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <el-dropdown trigger="click" @command="() => {}">
          <el-button :icon="Setting" size="small">
            列设置
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="col in columnConfig"
                :key="col.prop"
                :divided="col.prop === 'id'"
                @click.stop
              >
                <el-checkbox
                  v-model="columnVisible[col.prop]"
                  @change="() => handleColumnToggle(col.prop)"
                  @click.stop
                >
                  {{ col.label }}
                </el-checkbox>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div>
        <el-button :icon="Refresh" size="small" @click="handleReset">重置所有筛选</el-button>
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table
      ref="tableRef"
      :data="tableData"
      v-loading="loading"
      stripe
      border
      height="calc(100vh - 250px)"
      style="width: 100%; table-layout: auto"
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
      <!-- 动态生成列 -->
      <template v-for="col in columnConfig" :key="col.prop">
        <el-table-column
          v-if="columnVisible[col.prop]"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.minWidth || 120"
          :fixed="col.fixed"
          :sortable="col.sortable ? 'custom' : false"
        >
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                v-if="col.sortable"
                class="sort-icon" 
                :style="{ color: getSortIconColor(col.prop) }"
                @click.stop="handleHeaderSortClick(col.prop)"
              >
                <component :is="getSortIcon(col.prop)" />
              </el-icon>
              <span>{{ col.label }}</span>
              <el-popover
                v-if="col.filterable && col.filterType !== 'none'"
                placement="bottom"
                :width="getFilterPopoverWidth(col.filterType)"
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
                      @keyup.enter="handleFilterChange"
                      @clear="handleFilterChange"
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
                      <el-input-number
                        v-model="filterInputs[`${col.prop}Value`]"
                        placeholder="值"
                        size="small"
                        :min="0"
                        :controls="false"
                        style="flex: 1"
                        @keyup.enter="handleFilterChange"
                        @click.stop
                      />
                    </div>
                    <div style="margin-top: 8px;">
                      <el-button type="primary" size="small" @click="handleFilterChange" style="width: 100%">应用筛选</el-button>
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
                        <el-input-number
                          v-model="filter.value"
                          placeholder="值（按回车确认）"
                          size="small"
                          :min="0"
                          :controls="false"
                          style="flex: 1; min-width: 80px"
                          @keyup.enter="handleFilterChange"
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
                    <div style="margin-top: 8px;">
                      <el-button type="primary" size="small" @click="handleFilterChange" style="width: 100%">应用筛选</el-button>
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
                    <div style="margin-top: 8px;">
                      <el-button type="primary" size="small" @click.stop="() => handleFilterChangeAndClose(col.prop)" style="width: 100%">应用</el-button>
                    </div>
                  </template>
                  
                  <!-- 日期筛选 -->
                  <template v-else-if="col.filterType === 'date'">
                    <el-input
                      v-model="filterInputs[col.prop]"
                      placeholder="YYYY-MM-DD（按回车确认）"
                      size="small"
                      clearable
                      @keyup.enter="handleFilterChange"
                      @clear="handleFilterChange"
                    />
                    <div style="margin-top: 8px;">
                      <el-button type="primary" size="small" @click="handleFilterChange" style="width: 100%">应用筛选</el-button>
                    </div>
                  </template>
                </div>
              </el-popover>
            </div>
          </div>
        </template>
        <template #default="scope">
          <template v-if="col.type === 'number' && col.prop === 'salary'">
            ¥{{ scope.row[col.prop]?.toLocaleString() ?? '-' }}
          </template>
          <template v-else-if="col.filterType === 'multi-select'">
            <el-tag
              v-if="col.prop === 'status'"
              :type="getStatusType(scope.row[col.prop])"
              size="small"
            >
              {{ scope.row[col.prop] ?? '-' }}
            </el-tag>
            <el-tag v-else>
              {{ scope.row[col.prop] ?? '-' }}
            </el-tag>
          </template>
          <template v-else>
            {{ scope.row[col.prop] ?? '-' }}
          </template>
        </template>
        </el-table-column>
      </template>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :page-sizes="[50, 100, 200, 500]"
      :total="pagination.total"
      layout="total, sizes, prev, pager, next, jumper"
      style="margin-top: 16px; justify-content: flex-end"
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Delete, Setting, ArrowDown, ArrowUp, Sort, Filter } from '@element-plus/icons-vue'
import { TableData, FilterParams, NumberFilter, RowDetail, ColumnConfig } from '../types'
import { dataApi } from '../api/data'
import type { ElTable } from 'element-plus'

// 响应式数据
const tableData = ref<TableData[]>([])
const loading = ref(false)
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

// Popover 显示状态（用于保持多选筛选的悬浮框打开）
const popoverVisible = reactive<Record<string, boolean>>({})

// 需要保持打开的 popover（多选筛选时）
const keepOpenPopovers = reactive<Set<string>>(new Set())

// 使用定时器持续检查并保持需要打开的 popover
const keepPopoverOpen = () => {
  keepOpenPopovers.forEach(prop => {
    if (!popoverVisible[prop]) {
      popoverVisible[prop] = true
    }
  })
}

// 启动定时器，每100ms检查一次
let keepOpenInterval: number | null = null
onMounted(() => {
  keepOpenInterval = setInterval(keepPopoverOpen, 100) as unknown as number
})

// 组件卸载时清理定时器  
onUnmounted(() => {
  if (keepOpenInterval !== null) {
    clearInterval(keepOpenInterval)
  }
})

// 初始化列显示状态
const initColumnVisible = (columns: ColumnConfig[]) => {
  columns.forEach(col => {
    columnVisible[col.prop] = true  // 默认全部显示
  })
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

// 排序状态
const sortInfo = reactive({
  prop: undefined as string | undefined,
  order: undefined as 'ascending' | 'descending' | null | undefined
})

// 加载筛选选项
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
    console.log('列配置加载成功:', columnConfig.value)
  } catch (error) {
    console.error('加载列配置失败:', error)
    ElMessage.error('加载列配置失败，使用默认配置')
    // 使用默认列配置
    columnConfig.value = defaultColumns
    initColumnVisible(defaultColumns)
    initFilterForm(defaultColumns)
    console.log('使用默认列配置:', columnConfig.value)
  }
}

const loadFilterOptions = async () => {
  // 筛选选项现在从列配置的 options 字段获取，不需要单独加载
  // 如果后端提供了额外的筛选选项API，可以在这里加载
  try {
    const options = await dataApi.getFilters()
    // 动态设置筛选选项
    if (options.departments) filterOptions['department'] = options.departments
    if (options.statuses) filterOptions['status'] = options.statuses
    // 可以扩展其他字段的选项加载
  } catch (error) {
    console.error('加载筛选选项失败:', error)
  }
}

// 加载数据
const loadData = async (keepSelectedRow = false) => {
  console.log('📊 loadData 被调用', new Error().stack?.split('\n')[2]?.trim())
  loading.value = true
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
          console.log(`  [构建筛选] ${prop}: selectValue =`, selectValue, '类型:', typeof selectValue, 'isArray:', Array.isArray(selectValue))
          if (Array.isArray(selectValue) && selectValue.length > 0) {
            filters[prop] = selectValue.length === 1 ? selectValue[0] : selectValue
            console.log(`  [构建筛选] ${prop}: 设置为`, filters[prop])
          } else if (selectValue !== undefined && selectValue !== null && selectValue !== '') {
            filters[prop] = selectValue
            console.log(`  [构建筛选] ${prop}: 设置为单个值`, filters[prop])
          } else {
            console.log(`  [构建筛选] ${prop}: 值为空，跳过`)
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
        console.log('查询选中行位置，rowId:', selectedRowId.value, 'filters:', JSON.stringify(requestFilters))
        const positionResponse = await dataApi.getRowPosition(selectedRowId.value, requestFilters)
        console.log('选中行位置查询结果:', positionResponse)
        if (positionResponse.found) {
          // 计算选中行应该在哪一页
          targetPage = Math.floor(positionResponse.position / pagination.pageSize) + 1
          console.log(`选中行位置: ${positionResponse.position}, 跳转到第 ${targetPage} 页`)
        } else {
          // 选中行不在筛选结果中，清除选中状态
          console.log('选中行不在筛选结果中，清除选中状态')
          selectedRowId.value = null
          shouldKeepSelected = false
        }
      } catch (error) {
        console.error('查询选中行位置失败:', error)
        // 查询失败时，不清除选中状态，继续尝试在当前页查找
        console.log('查询失败，保持选中状态，尝试在当前页查找')
      }
    }

    const requestParams = {
      page: targetPage,
      pageSize: pagination.pageSize,
      filters: requestFilters,
      sortBy: sortInfo.prop,
      sortOrder: sortInfo.order
    }
    console.log('发送请求参数:', JSON.stringify(requestParams, null, 2))
    
    const response = await dataApi.getList(requestParams)
    
    console.log('收到响应，总数:', response.total)

    tableData.value = response.list
    pagination.total = response.total
    pagination.page = response.page
    pagination.pageSize = response.pageSize
    
    // 数据加载完成后，如果选中了行，需要恢复选中状态
    if (selectedRowId.value !== null && shouldKeepSelected) {
      await nextTick()
      // 查找选中行在当前页数据中的位置
      const selectedRow = tableData.value.find(row => row.id === selectedRowId.value)
      if (selectedRow) {
        // 设置表格的当前行，触发 highlight-current-row 高亮
        if (tableRef.value) {
          tableRef.value.setCurrentRow(selectedRow)
          console.log('已设置当前行:', selectedRow.id)
        }
        // 使用setTimeout确保DOM完全渲染后再滚动
        setTimeout(() => {
          scrollToSelectedRow()
        }, 100)
      } else {
        // 如果选中行不在当前页，但仍然在筛选结果中（已跳转到对应页面），尝试再次查找
        console.log('选中行不在当前页数据中，当前页数据ID列表:', tableData.value.map(r => r.id))
        // 延迟一点时间，确保表格已完全渲染
        setTimeout(() => {
          const row = tableData.value.find(r => r.id === selectedRowId.value)
          if (row && tableRef.value) {
            tableRef.value.setCurrentRow(row)
            console.log('延迟查找后设置当前行:', row.id)
            scrollToSelectedRow()
          } else {
            console.warn('延迟查找后仍未找到选中行，selectedRowId:', selectedRowId.value)
          }
        }, 150)
      }
    }
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.message || '加载数据失败'
    ElMessage.error(`加载数据失败: ${errorMsg}`)
    console.error('加载数据错误详情:', {
      error,
      response: error?.response,
      message: error?.message,
      stack: error?.stack
    })
  } finally {
    loading.value = false
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
      console.error('加载行详情错误:', error)
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
  console.log('选中行ID:', row.id)
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
    console.error('滚动到选中行失败:', error)
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
      console.error('滚动到选中行失败（备用方法）:', fallbackError)
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
        console.log(`[初始化] ${col.prop}: filterInputs =`, filterInputs[col.prop], 'filterForm =', filterForm[col.prop])
        // 初始化筛选选项
        if (col.options && col.options.length > 0) {
          filterOptions[col.prop] = col.options
          console.log(`[初始化] ${col.prop}: 选项数量 =`, col.options.length)
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
  console.log('🔄 同步筛选输入到表单...')
  console.log('filterInputs:', JSON.parse(JSON.stringify(filterInputs)))
  
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
        console.log(`  [同步] ${key}: 数组 ->`, filterForm[key])
      }
    } else {
      // 其他类型直接复制
      filterForm[key] = value
      if (value !== undefined && value !== null) {
        console.log(`  [同步] ${key}:`, filterForm[key])
      }
    }
  })
  
  console.log('filterForm:', JSON.parse(JSON.stringify(filterForm)))
}

// 处理筛选变化（仅在确认时调用）
const handleFilterChange = () => {
  console.log('🔵 筛选确认触发 - 同步并刷新数据')
  console.log('当前 filterInputs:', JSON.parse(JSON.stringify(filterInputs)))
  
  // 先同步输入状态到筛选表单
  syncFilterInputsToForm()
  
  // 等待一下确保数据同步完成
  nextTick(() => {
    // 保持选中行在当前页可见
    loadData(true)
  })
}

// 处理多选变化（仅保持悬浮框打开，不自动应用筛选）
const handleMultiSelectChange = (prop: string) => {
  console.log(`多选变化: ${prop} =`, filterInputs[prop])
  
  // 标记这个字段的 popover 需要保持打开
  keepOpenPopovers.add(prop)
  
  // 立即强制保持悬浮框打开
  popoverVisible[prop] = true
  
  // 在多个时机确保悬浮框保持打开
  nextTick(() => {
    popoverVisible[prop] = true
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
  // 重置排序
  sortInfo.prop = undefined
  sortInfo.order = undefined
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
  console.log('排序变化 - prop:', prop, 'order:', order, '完整参数:', { column, prop, order })
  
  // Element Plus 的 order 可能是 'ascending', 'descending', null 或 undefined
  // 更新排序状态
  if (prop && order) {
    sortInfo.prop = prop
    sortInfo.order = order === 'asc' ? 'ascending' : (order === 'desc' ? 'descending' : order)
  } else {
    // 清除排序
    sortInfo.prop = undefined
    sortInfo.order = undefined
  }
  
  console.log('更新后的排序状态:', { prop: sortInfo.prop, order: sortInfo.order })
  
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
  console.log(`列 ${prop} ${columnVisible[prop] ? '显示' : '隐藏'}`)
}

// 获取状态类型
const getStatusType = (status: string) => {
  const typeMap: Record<string, 'success' | 'danger' | 'warning'> = {
    '在职': 'success',
    '离职': 'danger',
    '试用期': 'warning'
  }
  return typeMap[status] || ''
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

// 初始化
onMounted(async () => {
  try {
    await loadColumnsConfig()  // 先加载列配置，确保列可见性已初始化
    loadFilterOptions()
    // 确保列配置加载完成后再加载数据
    await loadData()
    console.log('初始化完成，数据已加载')
  } catch (error) {
    console.error('初始化失败:', error)
    // 即使列配置加载失败，也尝试加载数据（使用默认配置）
    if (columnConfig.value.length === 0) {
      columnConfig.value = defaultColumns
      initColumnVisible(defaultColumns)
      initFilterForm(defaultColumns)
    }
    await loadData()
  }
})
</script>

<style scoped>
.table-card {
  margin: 16px;
  height: calc(100vh - 32px);
  width: calc(100% - 32px);
  max-width: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

:deep(.el-card__body) {
  padding: 16px;
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

/* 标题行样式（包含排序图标和标题） */
.header-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.header-title-row > span {
  font-weight: 600;
  margin-bottom: 0;
}

/* 排序图标样式 */
.sort-icon {
  cursor: pointer;
  font-size: 14px;
  transition: color 0.2s;
  flex-shrink: 0;
}

.sort-icon:hover {
  color: #409eff !important;
}

/* 筛选图标样式 */
.filter-icon {
  cursor: pointer;
  font-size: 14px;
  transition: color 0.2s;
  flex-shrink: 0;
  margin-left: auto;
}

.filter-icon:hover {
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
</style>


