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
      highlight-current-row
      :row-class-name="getRowClassName"
    >
      <!-- 展开列 -->
      <el-table-column type="expand" width="50" fixed="left">
        <template #default="{ row }">
          <div class="expand-detail">
            <div class="detail-item">
              <span class="detail-label">ID:</span>
              <span class="detail-value">{{ row.id }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">姓名:</span>
              <span class="detail-value">{{ row.name }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">邮箱:</span>
              <span class="detail-value">{{ row.email }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">年龄:</span>
              <span class="detail-value">{{ row.age }} 岁</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">部门:</span>
              <span class="detail-value">
                <el-tag>{{ row.department }}</el-tag>
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">薪资:</span>
              <span class="detail-value">¥{{ row.salary.toLocaleString() }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">状态:</span>
              <span class="detail-value">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ row.status }}
                </el-tag>
              </span>
            </div>
            <div class="detail-item">
              <span class="detail-label">创建时间:</span>
              <span class="detail-value">{{ row.createTime }}</span>
            </div>
          </div>
        </template>
        <template #header>
          <span style="font-size: 14px; font-weight: 600;">+</span>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.id" prop="id" label="ID" min-width="120" fixed="left" sortable="custom">
        <template #header>
          <div class="column-header">
            <span>ID</span>
            <div style="display: flex; gap: 4px; margin-top: 4px">
              <el-select
                v-model="filterForm.idOperator"
                placeholder="操作符"
                size="small"
                clearable
                style="width: 60px"
                @change="handleFilterChange"
              >
                <el-option label="=" value="=" />
                <el-option label=">" value=">" />
                <el-option label="<" value="<" />
                <el-option label=">=" value=">=" />
                <el-option label="<=" value="<=" />
              </el-select>
              <el-input-number
                v-model="filterForm.idValue"
                placeholder="值"
                size="small"
                :min="0"
                :controls="false"
                style="flex: 1"
                @change="handleFilterChange"
              />
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.name" prop="name" label="姓名" min-width="120" sortable="custom">
        <template #header>
          <div class="column-header">
            <span>姓名</span>
            <el-input
              v-model="filterForm.name"
              placeholder="筛选姓名"
              size="small"
              clearable
              style="width: 100%; margin-top: 4px"
              @input="handleFilterChange"
            >
              <template #prefix>
                <el-icon style="font-size: 12px;"><Search /></el-icon>
              </template>
            </el-input>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.email" prop="email" label="邮箱" min-width="180">
        <template #header>
          <div class="column-header">
            <span>邮箱</span>
            <el-input
              v-model="filterForm.email"
              placeholder="筛选邮箱"
              size="small"
              clearable
              style="width: 100%; margin-top: 4px"
              @input="handleFilterChange"
            />
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.age" prop="age" label="年龄" min-width="200" sortable="custom">
        <template #header>
          <div class="column-header">
            <span>年龄</span>
            <div class="filter-group">
              <div
                v-for="(filter, index) in filterForm.ageFilters"
                :key="index"
                style="display: flex; gap: 4px; margin-top: 4px; align-items: center"
              >
                <el-select
                  v-if="index > 0"
                  v-model="filterForm.ageLogic"
                  size="small"
                  style="width: 50px"
                  @change="handleFilterChange"
                >
                  <el-option label="AND" value="AND" />
                  <el-option label="OR" value="OR" />
                </el-select>
                <el-select
                  v-model="filter.operator"
                  placeholder="操作符"
                  size="small"
                  clearable
                  style="width: 60px"
                  @change="handleFilterChange"
                >
                  <el-option label="=" value="=" />
                  <el-option label=">" value=">" />
                  <el-option label="<" value="<" />
                  <el-option label=">=" value=">=" />
                  <el-option label="<=" value="<=" />
                </el-select>
                <el-input-number
                  v-model="filter.value"
                  placeholder="值"
                  size="small"
                  :min="0"
                  :max="100"
                  :controls="false"
                  style="flex: 1; min-width: 80px"
                  @change="handleFilterChange"
                />
                <el-button
                  v-if="filterForm.ageFilters.length > 1"
                  :icon="Delete"
                  size="small"
                  text
                  type="danger"
                  @click="removeAgeFilter(index)"
                />
              </div>
              <el-button
                size="small"
                text
                type="primary"
                style="margin-top: 4px; width: 100%"
                @click="addAgeFilter"
              >
                + 添加条件
              </el-button>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.department" prop="department" label="部门" min-width="120">
        <template #header>
          <div class="column-header">
            <span>部门</span>
            <el-select
              v-model="filterForm.department"
              placeholder="筛选部门"
              size="small"
              clearable
              style="width: 100%; margin-top: 4px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="dept in filterOptions.departments"
                :key="dept"
                :label="dept"
                :value="dept"
              />
            </el-select>
          </div>
        </template>
        <template #default="scope">
          <el-tag>{{ scope.row.department }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.salary" prop="salary" label="薪资" min-width="200" sortable="custom">
        <template #header>
          <div class="column-header">
            <span>薪资</span>
            <div class="filter-group">
              <div
                v-for="(filter, index) in filterForm.salaryFilters"
                :key="index"
                style="display: flex; gap: 4px; margin-top: 4px; align-items: center"
              >
                <el-select
                  v-if="index > 0"
                  v-model="filterForm.salaryLogic"
                  size="small"
                  style="width: 50px"
                  @change="handleFilterChange"
                >
                  <el-option label="AND" value="AND" />
                  <el-option label="OR" value="OR" />
                </el-select>
                <el-select
                  v-model="filter.operator"
                  placeholder="操作符"
                  size="small"
                  clearable
                  style="width: 60px"
                  @change="handleFilterChange"
                >
                  <el-option label="=" value="=" />
                  <el-option label=">" value=">" />
                  <el-option label="<" value="<" />
                  <el-option label=">=" value=">=" />
                  <el-option label="<=" value="<=" />
                </el-select>
                <el-input-number
                  v-model="filter.value"
                  placeholder="值"
                  size="small"
                  :min="0"
                  :controls="false"
                  style="flex: 1; min-width: 80px"
                  @change="handleFilterChange"
                />
                <el-button
                  v-if="filterForm.salaryFilters.length > 1"
                  :icon="Delete"
                  size="small"
                  text
                  type="danger"
                  @click="removeSalaryFilter(index)"
                />
              </div>
              <el-button
                size="small"
                text
                type="primary"
                style="margin-top: 4px; width: 100%"
                @click="addSalaryFilter"
              >
                + 添加条件
              </el-button>
            </div>
          </div>
        </template>
        <template #default="scope">
          ¥{{ scope.row.salary.toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.status" prop="status" label="状态" min-width="120">
        <template #header>
          <div class="column-header">
            <span>状态</span>
            <el-select
              v-model="filterForm.status"
              placeholder="筛选状态"
              size="small"
              clearable
              style="width: 100%; margin-top: 4px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="status in filterOptions.statuses"
                :key="status"
                :label="status"
                :value="status"
              />
            </el-select>
          </div>
        </template>
        <template #default="scope">
          <el-tag
            :type="getStatusType(scope.row.status)"
            size="small"
          >
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.createTime" prop="createTime" label="创建时间" min-width="120" sortable="custom">
        <template #header>
          <div class="column-header">
            <span>创建时间</span>
            <el-input
              v-model="filterForm.createTime"
              placeholder="YYYY-MM-DD"
              size="small"
              clearable
              style="width: 100%; margin-top: 4px"
              @input="handleFilterChange"
            />
          </div>
        </template>
      </el-table-column>
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
import { ref, reactive, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Delete, Setting, ArrowDown } from '@element-plus/icons-vue'
import { TableData, FilterParams, NumberFilter } from '../types'
import { dataApi } from '../api/data'
import type { ElTable } from 'element-plus'

// 响应式数据
const tableData = ref<TableData[]>([])
const loading = ref(false)
const selectedRowId = ref<number | null>(null) // 选中的行ID
const tableRef = ref<InstanceType<typeof ElTable>>() // 表格引用
const filterOptions = reactive({
  departments: [] as string[],
  statuses: [] as string[]
})

// 列配置
const columnConfig = [
  { prop: 'id', label: 'ID' },
  { prop: 'name', label: '姓名' },
  { prop: 'email', label: '邮箱' },
  { prop: 'age', label: '年龄' },
  { prop: 'department', label: '部门' },
  { prop: 'salary', label: '薪资' },
  { prop: 'status', label: '状态' },
  { prop: 'createTime', label: '创建时间' }
]

// 列显示状态（默认全部显示）
const columnVisible = reactive<Record<string, boolean>>({
  id: true,
  name: true,
  email: true,
  age: true,
  department: true,
  salary: true,
  status: true,
  createTime: true
})

const filterForm = reactive({
  // ID筛选
  idOperator: undefined as '=' | '>' | '<' | '>=' | '<=' | undefined,
  idValue: undefined as number | undefined,
  // 文本筛选
  name: undefined as string | undefined,
  email: undefined as string | undefined,
  department: undefined as string | undefined,
  status: undefined as string | undefined,
  // 年龄筛选（支持多个条件）
  ageFilters: [
    {
      operator: undefined as '=' | '>' | '<' | '>=' | '<=' | undefined,
      value: undefined as number | undefined
    }
  ] as NumberFilter[],
  ageLogic: 'AND' as 'AND' | 'OR',
  // 薪资筛选（支持多个条件）
  salaryFilters: [
    {
      operator: undefined as '=' | '>' | '<' | '>=' | '<=' | undefined,
      value: undefined as number | undefined
    }
  ] as NumberFilter[],
  salaryLogic: 'AND' as 'AND' | 'OR',
  // 日期筛选
  createTime: undefined as string | undefined,
  // 兼容旧版本的字段（保留用于向后兼容）
  ageMin: undefined as number | undefined,
  ageMax: undefined as number | undefined,
  salaryMin: undefined as number | undefined,
  salaryMax: undefined as number | undefined
})

const pagination = reactive({
  page: 1,
  pageSize: 100,
  total: 0
})

// 加载筛选选项
const loadFilterOptions = async () => {
  try {
    const options = await dataApi.getFilters()
    filterOptions.departments = options.departments
    filterOptions.statuses = options.statuses
  } catch (error) {
    console.error('加载筛选选项失败:', error)
  }
}

// 加载数据
const loadData = async (keepSelectedRow = false) => {
  loading.value = true
  try {
    const filters: FilterParams = {}
    
    // ID筛选（支持操作符）
    if (filterForm.idOperator && filterForm.idValue !== undefined) {
      filters.id = {
        operator: filterForm.idOperator,
        value: filterForm.idValue
      }
    }
    
    // 文本筛选
    if (filterForm.name) filters.name = filterForm.name
    if (filterForm.email) filters.email = filterForm.email
    if (filterForm.department) filters.department = filterForm.department
    if (filterForm.status) filters.status = filterForm.status
    
    // 年龄筛选（支持多个条件组合和AND/OR逻辑）
    const ageFilters = filterForm.ageFilters.filter(
      f => f.operator && f.value !== undefined
    )
    if (ageFilters.length > 0) {
      if (ageFilters.length === 1) {
        filters.age = ageFilters[0]
      } else {
        filters.age = {
          filters: ageFilters,
          logic: filterForm.ageLogic
        }
      }
    }
    
    // 薪资筛选（支持多个条件组合和AND/OR逻辑）
    const salaryFilters = filterForm.salaryFilters.filter(
      f => f.operator && f.value !== undefined
    )
    if (salaryFilters.length > 0) {
      if (salaryFilters.length === 1) {
        filters.salary = salaryFilters[0]
      } else {
        filters.salary = {
          filters: salaryFilters,
          logic: filterForm.salaryLogic
        }
      }
    }
    
    // 日期筛选
    if (filterForm.createTime) filters.createTime = filterForm.createTime

    // 发送筛选条件（只有在有筛选条件时才发送）
    const requestFilters = Object.keys(filters).length > 0 ? filters : undefined
    
    // 如果保持选中行，需要先查询选中行在新筛选条件下的位置
    let targetPage = pagination.page
    if (keepSelectedRow && selectedRowId.value !== null) {
      try {
        const positionResponse = await dataApi.getRowPosition(selectedRowId.value, requestFilters)
        if (positionResponse.found) {
          // 计算选中行应该在哪一页
          targetPage = Math.floor(positionResponse.position / pagination.pageSize) + 1
          console.log(`选中行位置: ${positionResponse.position}, 跳转到第 ${targetPage} 页`)
        } else {
          // 选中行不在筛选结果中，清除选中状态
          selectedRowId.value = null
        }
      } catch (error) {
        console.error('查询选中行位置失败:', error)
      }
    }

    const response = await dataApi.getList({
      page: targetPage,
      pageSize: pagination.pageSize,
      filters: requestFilters
    })
    
    console.log('收到响应，总数:', response.total)

    tableData.value = response.list
    pagination.total = response.total
    pagination.page = response.page
    pagination.pageSize = response.pageSize
    
    // 数据加载完成后，如果选中了行，滚动到选中行
    if (selectedRowId.value !== null) {
      await nextTick()
      // 使用setTimeout确保DOM完全渲染
      setTimeout(() => {
        scrollToSelectedRow()
      }, 100)
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

// 处理筛选变化
const handleFilterChange = () => {
  // 保持选中行在当前页可见
  loadData(true)
}

// 添加年龄筛选条件
const addAgeFilter = () => {
  filterForm.ageFilters.push({
    operator: undefined,
    value: undefined
  })
}

// 移除年龄筛选条件
const removeAgeFilter = (index: number) => {
  filterForm.ageFilters.splice(index, 1)
  if (filterForm.ageFilters.length === 0) {
    addAgeFilter()
  }
  handleFilterChange()
}

// 添加薪资筛选条件
const addSalaryFilter = () => {
  filterForm.salaryFilters.push({
    operator: undefined,
    value: undefined
  })
}

// 移除薪资筛选条件
const removeSalaryFilter = (index: number) => {
  filterForm.salaryFilters.splice(index, 1)
  if (filterForm.salaryFilters.length === 0) {
    addSalaryFilter()
  }
  handleFilterChange()
}

// 重置筛选
const handleReset = () => {
  filterForm.idOperator = undefined
  filterForm.idValue = undefined
  filterForm.name = undefined
  filterForm.email = undefined
  filterForm.department = undefined
  filterForm.status = undefined
  filterForm.ageFilters = [{ operator: undefined, value: undefined }]
  filterForm.ageLogic = 'AND'
  filterForm.salaryFilters = [{ operator: undefined, value: undefined }]
  filterForm.salaryLogic = 'AND'
  filterForm.createTime = undefined
  filterForm.ageMin = undefined
  filterForm.ageMax = undefined
  filterForm.salaryMin = undefined
  filterForm.salaryMax = undefined
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
  // 这里可以实现服务端排序，当前为前端排序提示
  console.log('排序:', prop, order)
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

// 初始化
onMounted(() => {
  loadFilterOptions()
  loadData()
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


