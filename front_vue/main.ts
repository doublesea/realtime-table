import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
// @ts-ignore
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import VXETable from 'vxe-table'
import 'vxe-table/lib/style.css'
import VxeUI from 'vxe-pc-ui'
import 'vxe-pc-ui/lib/style.css'
import App from './App.vue'
import './index.css'

// 导出挂载函数，支持多实例
export function mountTable(container: string | HTMLElement, props: any = {}) {
  console.log('Mounting NiceTable to:', container, 'with props:', props)
  const app = createApp(App, props)

  // 注册Element Plus图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.use(ElementPlus, {
    locale: zhCn,
  })
  app.use(VxeUI)
  app.use(VXETable)

  app.mount(container)
  return app
}

// 全局暴露，方便在非模块环境下调用
if (typeof window !== 'undefined') {
  (window as any).mountNiceTable = mountTable
}

// 兼容旧的单实例挂载方式
if (typeof document !== 'undefined') {
  const rootEl = document.getElementById('root')
  // 只有在没有显式指定不自动挂载的情况下才自动挂载
  if (rootEl && !rootEl.dataset.vMounted) {
    mountTable(rootEl, {
      tableId: rootEl.dataset.tableId,
      defaultVersion: rootEl.dataset.defaultVersion,
      apiUrl: ''
    })
    rootEl.dataset.vMounted = 'true'
  }
}
