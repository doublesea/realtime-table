<template>
  <div class="app">
    <DataTable v-if="currentVersion === 'element'" ref="dataTableRef" api-url="" />
    <VxeDataTable v-if="currentVersion === 'vxe'" ref="dataTableRef" api-url="" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import DataTable from './components/DataTable.vue'
import VxeDataTable from './components/VxeDataTable.vue'

const currentVersion = ref('element')
const dataTableRef = ref()

// 获取默认版本从 DOM
const getDefaultVersion = (): string => {
  const root = document.getElementById('root')
  return root?.dataset.defaultVersion || 'element'
}

onMounted(() => {
  currentVersion.value = getDefaultVersion()
})

// 获取 tableId 从 DOM
const getTableId = (): string | null => {
  const root = document.getElementById('root')
  return root?.dataset.tableId || null
}

// 注册暴露的实例到全局注册表
const registerInstance = () => {
  const tableId = getTableId()
  if (tableId && dataTableRef.value) {
    // 注册到全局注册表
    const registry = (window as any).__nice_table_registry || {}
    registry[tableId] = {
      refreshData: () => dataTableRef.value?.refreshData(),
      refreshColumns: () => dataTableRef.value?.refreshColumns(),
      switchVersion: (version: string) => { currentVersion.value = version }
    }
    ;(window as any).__nice_table_registry = registry
    console.log('NiceTable instance registered:', tableId, registry, 'Version:', currentVersion.value)
    
    // 触发自定义事件，通知 Python 端实例已就绪
    window.dispatchEvent(new CustomEvent('nice-table-ready', { detail: { tableId } }))
    return true
  }
  return false
}

// 监听版本切换，重新注册实例
watch(currentVersion, async () => {
  await nextTick()
  registerInstance()
})

onMounted(async () => {
  // 等待多个 tick，确保 DOM 完全渲染
  await nextTick()
  await nextTick()
  
  // 如果第一次尝试失败，使用轮询重试
  if (!registerInstance()) {
    let retries = 0
    const maxRetries = 20
    const interval = setInterval(() => {
      retries++
      if (registerInstance() || retries >= maxRetries) {
        clearInterval(interval)
        if (retries >= maxRetries) {
          console.warn('Failed to register NiceTable instance after', maxRetries, 'retries')
        }
      }
    }, 200)
  }
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


