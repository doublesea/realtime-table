<template>
  <div class="app">
    <DataTable 
      v-if="currentVersion === 'element'" 
      ref="dataTableRef" 
      api-url="" 
      :table-id="tableId"
      :initial-sort="globalSort"
      @sort-change="updateGlobalSort"
    />
    <VxeDataTable 
      v-if="currentVersion === 'vxe'" 
      ref="dataTableRef" 
      api-url="" 
      :table-id="tableId"
      :initial-sort="globalSort"
      @sort-change="updateGlobalSort"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, watch, computed } from 'vue'
import DataTable from './components/DataTable.vue'
import VxeDataTable from './components/VxeDataTable.vue'

const props = defineProps<{
  tableId?: string
  defaultVersion?: string
  apiUrl?: string
}>()

const currentVersion = ref(props.defaultVersion || 'element')
const dataTableRef = ref()

// 全局共享的排序状态
const globalSort = reactive({
  prop: 'id',
  order: 'ascending' as 'ascending' | 'descending' | null | undefined
})

const updateGlobalSort = (newSort: { prop: string | undefined, order: any }) => {
  globalSort.prop = newSort.prop || 'id'
  globalSort.order = newSort.order || 'ascending'
  console.log('Global sort updated:', globalSort)
}

const tableId = computed(() => {
  if (props.tableId) return props.tableId
  // 这里的 id="root" 仅作为极少数情况下的兼容兜底，新架构下通常走 props
  const root = document.getElementById('root')
  return root?.dataset.tableId || null
})

// 获取默认版本从 DOM（作为备选）
const getDefaultVersion = (): string => {
  if (props.defaultVersion) return props.defaultVersion
  const root = document.getElementById('root')
  return root?.dataset.defaultVersion || 'element'
}

onMounted(() => {
  if (!props.defaultVersion) {
    currentVersion.value = getDefaultVersion()
  }
})

// 注册暴露的实例到全局注册表
const registerInstance = () => {
  const tid = tableId.value
  if (!tid) return false

  // 确保注册表存在
  const registry = (window as any).__nice_table_registry || {}
  
  // 注册/更新实例方法
  registry[tid] = {
    refreshData: () => dataTableRef.value?.refreshData?.(),
    refreshColumns: () => dataTableRef.value?.refreshColumns?.(),
    switchVersion: (version: string) => { currentVersion.value = version },
    _isPlaceholder: !dataTableRef.value
  }
  
  ;(window as any).__nice_table_registry = registry
  
  if (dataTableRef.value) {
    console.log(`NiceTable [${tid}] registered (Version: ${currentVersion.value})`)
    window.dispatchEvent(new CustomEvent('nice-table-ready', { detail: { tableId: tid } }))
    return true
  }
  return false
}

// 监听 ID 和版本变化，确保实时注册
watch([tableId, currentVersion], () => {
  nextTick(registerInstance)
}, { immediate: true })

// 监听 dataTableRef 变化 (当组件切换时)
watch(dataTableRef, () => {
  registerInstance()
})

onMounted(() => {
  // 兜底：如果没通过 props 传版本，尝试从 dataset 获取
  if (!props.defaultVersion) {
    const root = document.getElementById('root')
    if (root?.dataset.defaultVersion) {
      currentVersion.value = root.dataset.defaultVersion
    }
  }
  
  // 间隔重试，直到 ref 准备就绪（处理异步挂载）
  let retries = 0
  const timer = setInterval(() => {
    if (registerInstance() || ++retries > 50) clearInterval(timer)
  }, 200)
})

defineExpose({
  refreshData: () => dataTableRef.value?.refreshData(),
  refreshColumns: () => dataTableRef.value?.refreshColumns(),
  switchVersion: (version: string) => { currentVersion.value = version }
})
</script>

<style scoped>
.app {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>


