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
      <el-table-column v-if="columnVisible.id" prop="id" label="ID" min-width="120" fixed="left" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('id') }"
                @click.stop="handleHeaderSortClick('id')"
              >
                <component :is="getSortIcon('id')" />
              </el-icon>
              <span>ID</span>
              <el-popover
                placement="bottom"
                :width="280"
                trigger="click"
                :popper-options="{ modifiers: [{ name: 'preventOverflow', options: { padding: 8 } }, { name: 'computeStyles', options: { gpuAcceleration: false } }] }"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('id') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover" @click.stop>
                  <div style="margin-bottom: 8px; font-weight: 600;">ID筛选</div>
                  <div style="display: flex; gap: 8px; align-items: center;">
                    <el-select
                      v-model="filterForm.idOperator"
                      placeholder="操作符"
                      size="small"
                      clearable
                      style="width: 80px"
                      :teleported="false"
                      @change="handleFilterChange"
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
                      v-model="filterForm.idValue"
                      placeholder="值"
                      size="small"
                      :min="0"
                      :controls="false"
                      style="flex: 1"
                      @change="handleFilterChange"
                      @click.stop
                    />
                  </div>
                </div>
              </el-popover>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.name" prop="name" label="姓名" min-width="120" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('name') }"
                @click.stop="handleHeaderSortClick('name')"
              >
                <component :is="getSortIcon('name')" />
              </el-icon>
              <span>姓名</span>
              <el-popover
                placement="bottom"
                :width="250"
                trigger="click"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('name') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover">
                  <div style="margin-bottom: 8px; font-weight: 600;">姓名筛选</div>
                  <el-input
                    v-model="filterForm.name"
                    placeholder="筛选姓名"
                    size="small"
                    clearable
                    @input="handleFilterChange"
                  >
                    <template #prefix>
                      <el-icon style="font-size: 12px;"><Search /></el-icon>
                    </template>
                  </el-input>
                </div>
              </el-popover>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.email" prop="email" label="邮箱" min-width="180" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('email') }"
                @click.stop="handleHeaderSortClick('email')"
              >
                <component :is="getSortIcon('email')" />
              </el-icon>
              <span>邮箱</span>
              <el-popover
                placement="bottom"
                :width="250"
                trigger="click"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('email') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover">
                  <div style="margin-bottom: 8px; font-weight: 600;">邮箱筛选</div>
                  <el-input
                    v-model="filterForm.email"
                    placeholder="筛选邮箱"
                    size="small"
                    clearable
                    @input="handleFilterChange"
                  />
                </div>
              </el-popover>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.age" prop="age" label="年龄" min-width="200" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('age') }"
                @click.stop="handleHeaderSortClick('age')"
              >
                <component :is="getSortIcon('age')" />
              </el-icon>
              <span>年龄</span>
              <el-popover
                placement="bottom"
                :width="320"
                trigger="click"
                :popper-options="{ modifiers: [{ name: 'preventOverflow', options: { padding: 8 } }, { name: 'computeStyles', options: { gpuAcceleration: false } }] }"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('age') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover" @click.stop>
                  <div style="margin-bottom: 8px; font-weight: 600;">年龄筛选</div>
                  <div class="filter-group">
                    <div
                      v-for="(filter, index) in filterForm.ageFilters"
                      :key="index"
                      style="display: flex; gap: 8px; margin-top: 8px; align-items: center"
                    >
                      <el-select
                        v-if="index > 0"
                        v-model="filterForm.ageLogic"
                        size="small"
                        style="width: 60px"
                        :teleported="false"
                        @change="handleFilterChange"
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
                        @change="handleFilterChange"
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
                        placeholder="值"
                        size="small"
                        :min="0"
                        :max="100"
                        :controls="false"
                        style="flex: 1; min-width: 80px"
                        @change="handleFilterChange"
                        @click.stop
                      />
                      <el-button
                        v-if="filterForm.ageFilters.length > 1"
                        :icon="Delete"
                        size="small"
                        text
                        type="danger"
                        @click.stop="removeAgeFilter(index)"
                      />
                    </div>
                    <el-button
                      size="small"
                      text
                      type="primary"
                      style="margin-top: 8px; width: 100%"
                      @click.stop="addAgeFilter"
                    >
                      + 添加条件
                    </el-button>
                  </div>
                </div>
              </el-popover>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.department" prop="department" label="部门" min-width="120" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('department') }"
                @click.stop="handleHeaderSortClick('department')"
              >
                <component :is="getSortIcon('department')" />
              </el-icon>
              <span>部门</span>
              <el-popover
                placement="bottom"
                :width="250"
                trigger="click"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('department') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover">
                  <div style="margin-bottom: 8px; font-weight: 600;">部门筛选</div>
                  <el-select
                    v-model="filterForm.department"
                    placeholder="筛选部门（可多选）"
                    size="small"
                    clearable
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    style="width: 100%"
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
              </el-popover>
            </div>
          </div>
        </template>
        <template #default="scope">
          <el-tag>{{ scope.row.department }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.salary" prop="salary" label="薪资" min-width="200" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('salary') }"
                @click.stop="handleHeaderSortClick('salary')"
              >
                <component :is="getSortIcon('salary')" />
              </el-icon>
              <span>薪资</span>
              <el-popover
                placement="bottom"
                :width="320"
                trigger="click"
                :popper-options="{ modifiers: [{ name: 'preventOverflow', options: { padding: 8 } }, { name: 'computeStyles', options: { gpuAcceleration: false } }] }"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('salary') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover" @click.stop>
                  <div style="margin-bottom: 8px; font-weight: 600;">薪资筛选</div>
                  <div class="filter-group">
                    <div
                      v-for="(filter, index) in filterForm.salaryFilters"
                      :key="index"
                      style="display: flex; gap: 8px; margin-top: 8px; align-items: center"
                    >
                      <el-select
                        v-if="index > 0"
                        v-model="filterForm.salaryLogic"
                        size="small"
                        style="width: 60px"
                        :teleported="false"
                        @change="handleFilterChange"
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
                        @change="handleFilterChange"
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
                        placeholder="值"
                        size="small"
                        :min="0"
                        :controls="false"
                        style="flex: 1; min-width: 80px"
                        @change="handleFilterChange"
                        @click.stop
                      />
                      <el-button
                        v-if="filterForm.salaryFilters.length > 1"
                        :icon="Delete"
                        size="small"
                        text
                        type="danger"
                        @click.stop="removeSalaryFilter(index)"
                      />
                    </div>
                    <el-button
                      size="small"
                      text
                      type="primary"
                      style="margin-top: 8px; width: 100%"
                      @click.stop="addSalaryFilter"
                    >
                      + 添加条件
                    </el-button>
                  </div>
                </div>
              </el-popover>
            </div>
          </div>
        </template>
        <template #default="scope">
          ¥{{ scope.row.salary.toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column v-if="columnVisible.status" prop="status" label="状态" min-width="120" sortable="custom">
        <template #header>
          <div class="column-header">
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('status') }"
                @click.stop="handleHeaderSortClick('status')"
              >
                <component :is="getSortIcon('status')" />
              </el-icon>
              <span>状态</span>
              <el-popover
                placement="bottom"
                :width="250"
                trigger="click"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('status') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover">
                  <div style="margin-bottom: 8px; font-weight: 600;">状态筛选</div>
                  <el-select
                    v-model="filterForm.status"
                    placeholder="筛选状态（可多选）"
                    size="small"
                    clearable
                    multiple
                    collapse-tags
                    collapse-tags-tooltip
                    style="width: 100%"
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
              </el-popover>
            </div>
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
            <div class="header-title-row">
              <el-icon 
                class="sort-icon" 
                :style="{ color: getSortIconColor('createTime') }"
                @click.stop="handleHeaderSortClick('createTime')"
              >
                <component :is="getSortIcon('createTime')" />
              </el-icon>
              <span>创建时间</span>
              <el-popover
                placement="bottom"
                :width="250"
                trigger="click"
                @click.stop
              >
                <template #reference>
                  <el-icon 
                    class="filter-icon" 
                    :style="{ color: hasActiveFilter('createTime') ? '#409eff' : '#c0c4cc' }"
                    @click.stop
                  >
                    <Filter />
                  </el-icon>
                </template>
                <div class="filter-popover">
                  <div style="margin-bottom: 8px; font-weight: 600;">创建时间筛选</div>
                  <el-input
                    v-model="filterForm.createTime"
                    placeholder="YYYY-MM-DD"
                    size="small"
                    clearable
                    @input="handleFilterChange"
                  />
                </div>
              </el-popover>
            </div>
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
import { ref, reactive, onMounted, nextTick } from 'vue'
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
const filterOptions = reactive({
  departments: [] as string[],
  statuses: [] as string[]
})

// 行详情数据
const rowDetails = reactive<Record<number, RowDetail>>({})
const rowDetailsLoading = reactive<Record<number, boolean>>({})
const rowDetailsError = reactive<Record<number, string>>({})

// 列配置（从后端获取）
const columnConfig = ref<ColumnConfig[]>([])

// 列显示状态（动态生成）
const columnVisible = reactive<Record<string, boolean>>({})

// 初始化列显示状态
const initColumnVisible = (columns: ColumnConfig[]) => {
  columns.forEach(col => {
    columnVisible[col.prop] = true  // 默认全部显示
  })
}

const filterForm = reactive({
  // ID筛选
  idOperator: undefined as '=' | '>' | '<' | '>=' | '<=' | undefined,
  idValue: undefined as number | undefined,
  // 文本筛选
  name: undefined as string | undefined,
  email: undefined as string | undefined,
  department: [] as string[],  // 支持多选，初始为空数组
  status: [] as string[],  // 支持多选，初始为空数组
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

// 排序状态
const sortInfo = reactive({
  prop: undefined as string | undefined,
  order: undefined as 'ascending' | 'descending' | null | undefined
})

// 加载筛选选项
// 默认列配置（当后端加载失败时使用）
const defaultColumns: ColumnConfig[] = [
  { prop: 'id', label: 'ID', type: 'number', sortable: true, filterable: true, filterType: 'number', minWidth: 120 },
  { prop: 'name', label: '姓名', type: 'string', sortable: true, filterable: true, filterType: 'text', minWidth: 120 },
  { prop: 'email', label: '邮箱', type: 'string', sortable: true, filterable: true, filterType: 'text', minWidth: 180 },
  { prop: 'age', label: '年龄', type: 'number', sortable: true, filterable: true, filterType: 'number', minWidth: 120 },
  { prop: 'department', label: '部门', type: 'string', sortable: true, filterable: true, filterType: 'multi-select', minWidth: 120 },
  { prop: 'salary', label: '薪资', type: 'number', sortable: true, filterable: true, filterType: 'number', minWidth: 120 },
  { prop: 'status', label: '状态', type: 'string', sortable: true, filterable: true, filterType: 'multi-select', minWidth: 120 },
  { prop: 'createTime', label: '创建时间', type: 'date', sortable: true, filterable: true, filterType: 'date', minWidth: 120 }
]

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
    // 部门筛选（支持多选）
    if (filterForm.department && filterForm.department.length > 0) {
      filters.department = filterForm.department.length === 1 
        ? filterForm.department[0] 
        : filterForm.department
    }
    // 状态筛选（支持多选）
    if (filterForm.status && filterForm.status.length > 0) {
      filters.status = filterForm.status.length === 1 
        ? filterForm.status[0] 
        : filterForm.status
    }
    
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

// 动态初始化filterForm结构
const initFilterForm = (columns: ColumnConfig[]) => {
  // 清空现有的filterForm
  Object.keys(filterForm).forEach(key => {
    delete (filterForm as any)[key]
  })
  
  // 根据列配置动态初始化filterForm
  columns.forEach(col => {
    if (!col.filterable) return
    
    switch (col.filterType) {
      case 'number':
        // 数字类型：支持操作符和值
        ;(filterForm as any)[`${col.prop}Operator`] = undefined
        ;(filterForm as any)[`${col.prop}Value`] = undefined
        break
      case 'multi-select':
      case 'select':
        // 选择类型：数组或字符串
        ;(filterForm as any)[col.prop] = col.filterType === 'multi-select' ? [] : undefined
        break
      case 'text':
      case 'date':
        // 文本或日期类型：字符串
        ;(filterForm as any)[col.prop] = undefined
        break
    }
  })
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
  filterForm.department = []  // 多选字段重置为空数组
  filterForm.status = []  // 多选字段重置为空数组
  filterForm.ageFilters = [{ operator: undefined, value: undefined }]
  filterForm.ageLogic = 'AND'
  filterForm.salaryFilters = [{ operator: undefined, value: undefined }]
  filterForm.salaryLogic = 'AND'
  filterForm.createTime = undefined
  filterForm.ageMin = undefined
  filterForm.ageMax = undefined
  filterForm.salaryMin = undefined
  filterForm.salaryMax = undefined
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
  switch (prop) {
    case 'id':
      return !!(filterForm.idOperator && filterForm.idValue !== undefined)
    case 'name':
      return !!filterForm.name
    case 'email':
      return !!filterForm.email
    case 'age':
      return filterForm.ageFilters.some(f => f.operator && f.value !== undefined)
    case 'department':
      return filterForm.department && filterForm.department.length > 0
    case 'salary':
      return filterForm.salaryFilters.some(f => f.operator && f.value !== undefined)
    case 'status':
      return filterForm.status && filterForm.status.length > 0
    case 'createTime':
      return !!filterForm.createTime
    default:
      return false
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


