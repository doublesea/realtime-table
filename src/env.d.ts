/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// 扩展 Window 接口，添加 NiceTable 全局注册表
declare global {
  interface Window {
    __nice_table_registry?: {
      [key: string]: {
        refreshData?: () => void | Promise<void>
        refreshColumns?: () => void | Promise<void>
      }
    }
  }
}


