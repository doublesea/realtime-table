import asyncio
import logging
import mimetypes
import uuid
from pathlib import Path

# 确保 MIME 类型正确
mimetypes.add_type('application/font-woff2', '.woff2')
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/x-font-ttf', '.ttf')
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from nicegui import app, ui

from data_table import FilterParams
from data_table import ColumnConfig, DataTable, generate_columns_config_from_dataframe

logger = logging.getLogger(__name__)


class NiceTable(ui.element):
    """封装后的 NiceGUI 数据表格控件"""

    _dist_path = Path(__file__).parent / 'dist'
    _static_mount_path = '/table-static'
    _static_route_name = 'nice_table_static'
    _css_asset: Optional[str] = None
    _js_asset: Optional[str] = None
    _assets_ready = False
    _router_registered = False
    # 使用字典存储所有活跃实例，key 为 uid
    _instances: Dict[str, 'NiceTable'] = {}
    # 存储所有连接的客户端，用于后台任务中发送消息
    _connected_clients: set = set()
    
    @classmethod
    def _parse_assets_from_html(cls) -> tuple:
        """从 dist/index.html 中解析 CSS 和 JS 文件名"""
        index_html = cls._dist_path / 'index.html'
        if not index_html.exists():
            raise FileNotFoundError(f'找不到 {index_html}，请先运行 npm run build')
        
        import re
        with open(index_html, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取 CSS 文件
        css_match = re.search(r'href=["\']([^"\']+\.css)["\']', content)
        # 提取 JS 文件
        js_match = re.search(r'src=["\']([^"\']+\.js)["\']', content)
        
        if not css_match or not js_match:
            raise ValueError(f'无法从 {index_html} 中解析资源文件路径')
        
        css_path = css_match.group(1)
        js_path = js_match.group(1)
        
        # 移除前导斜杠并处理相对路径
        css_path = css_path.lstrip('/').replace('./', '')
        js_path = js_path.lstrip('/').replace('./', '')
        
        # 再次确保去掉了 static/ (如果 base 还是旧的)
        if css_path.startswith('static/'):
            css_path = css_path[7:]
        if js_path.startswith('static/'):
            js_path = js_path[7:]
        
        return css_path, js_path

    def __init__(
        self,
        dataframe: pd.DataFrame,
        columns_config: Optional[List[ColumnConfig]] = None,
        page_size: int = 200,
        use_vxe: bool = False,
    ):
        super().__init__('div')
        if dataframe is None:
            raise ValueError('dataframe 不能为空')

        if columns_config is None:
            if dataframe.empty:
                raise ValueError('空 DataFrame 需要同时提供 columns_config')
            columns_config = generate_columns_config_from_dataframe(dataframe)
             
        base_df = dataframe.copy()
        if base_df.empty:
            base_df = pd.DataFrame(columns=[col.prop for col in columns_config])

        self.logic = DataTable(base_df, columns_config)
        self.page_size = page_size
        self.use_vxe = use_vxe
        self.uid = uuid.uuid4().hex
        self.container_id = f'nice-table-{self.uid}'

        # 注册实例
        NiceTable._instances[self.uid] = self
        
        self._ensure_assets()
        if not NiceTable._router_registered:
             self._ensure_routes()
        
        # 注册客户端连接监听器（只注册一次）
        if not hasattr(NiceTable, '_client_listener_registered'):
            @app.on_connect
            def register_client(client):
                NiceTable._connected_clients.add(client)
                logger.debug(f'客户端已连接: {client.id}')
            
            @app.on_disconnect
            def unregister_client(client):
                NiceTable._connected_clients.discard(client)
                logger.debug(f'客户端已断开: {client.id}')
            
            NiceTable._client_listener_registered = True
        
        self.classes('w-full h-full')

        with self:
            self._render_frontend()
    
    def delete(self):
        """销毁实例时从注册表中移除"""
        if self.uid in NiceTable._instances:
            del NiceTable._instances[self.uid]
        super().delete()

    # ---------- Public API ----------
    def add_data(self, records: List[Dict[str, Any]], refresh: bool = False) -> Dict[str, Any]:
        """向表格添加数据"""
        if not records:
            return {'success': False, 'added_count': 0}

        result = self.logic.add_data(records)
        if refresh:
            self.refresh_data()
        return result

    def update_source(self, dataframe: pd.DataFrame):
        """更新数据源 (使用外部管理的 DataFrame)"""
        result = self.logic.update_dataframe(dataframe)
        # 仅在列结构（增减、顺序）发生变化时才刷新列配置，避免频繁重绘导致筛选框关闭
        if result.get('structure_updated'):
            self.refresh_columns()
        self.refresh_data()

    def refresh_data(self):
        """通知前端刷新数据列表"""
        js_code = f"""
            const tid = '{self.uid}';
            const inst = window.__nice_table_registry && window.__nice_table_registry[tid];
            if (inst) {{
                try {{
                    inst.refreshData();
                }} catch (err) {{
                    console.error('NiceTable [' + tid + '] refreshData error:', err);
                }}
            }} else {{
                console.warn('NiceTable instance [' + tid + '] not found. If the tab is hidden, this is expected.');
            }}
        """
        
        # 尝试使用 UI context（如果在 UI 上下文中）
        try:
            ui.run_javascript(js_code)
        except RuntimeError:
            # 如果不在 UI 上下文中（如后台任务），使用 WebSocket 直接发送
            for client in NiceTable._connected_clients.copy():
                try:
                    client.run_javascript(js_code)
                except Exception as e:
                    logger.debug(f'向客户端 {{client.id}} 发送 JavaScript 失败: {{e}}')
                    # 如果客户端已断开，从集合中移除
                    NiceTable._connected_clients.discard(client)

    def refresh_columns(self):
        """通知前端刷新列设置"""
        ui.run_javascript(
            f"""
            const inst = window.__nice_table_registry && window.__nice_table_registry['{self.uid}'];
            if (inst && inst.refreshColumns) {{
                inst.refreshColumns();
            }}
            """
        )

    def switch_version(self, version: str):
        """切换前端表格版本 ('vxe' 或 'element')"""
        if version not in ['vxe', 'element']:
            raise ValueError("version 必须是 'vxe' 或 'element'")
        
        self.use_vxe = (version == 'vxe')
        js_code = f"""
            const inst = window.__nice_table_registry && window.__nice_table_registry['{self.uid}'];
            if (inst && inst.switchVersion) {{
                inst.switchVersion('{version}');
            }}
        """
        try:
            ui.run_javascript(js_code)
        except RuntimeError:
            for client in NiceTable._connected_clients.copy():
                try:
                    client.run_javascript(js_code)
                except Exception:
                    NiceTable._connected_clients.discard(client)

    def replace_dataframe(self, dataframe: pd.DataFrame, columns_config: Optional[List[ColumnConfig]] = None):
        """重新加载数据源"""
        if columns_config is None:
            columns_config = self.logic.columns_config
        self.logic = DataTable(dataframe.copy(), columns_config)
        self.refresh_columns()
        self.refresh_data()

    # ---------- Internal helpers ----------

    def _ensure_assets(self):
        """确保静态资源只挂载一次"""
        if NiceTable._assets_ready:
            return

        if not self._dist_path.exists():
            raise FileNotFoundError('dist 目录不存在，请先运行 npm run build')

        if self._static_mount_path not in [route.path for route in app.routes]:
            app.mount(
                self._static_mount_path,
                StaticFiles(directory=str(self._dist_path), html=True),
                name=self._static_route_name,
            )

        NiceTable._assets_ready = True

    def _render_frontend(self):
        """注入 Vue 构建产物"""
        # 如果还没有解析资源文件，先解析
        if NiceTable._css_asset is None or NiceTable._js_asset is None:
            NiceTable._css_asset, NiceTable._js_asset = NiceTable._parse_assets_from_html()
        
        css_url = f'{self._static_mount_path}/{self._css_asset}'
        js_url = f'{self._static_mount_path}/{self._js_asset}'

        # 注意：这里向前端传递了 uid，前端 fetch 时需要在 header 或 query 中带上
        # 目前前端代码可能只请求 /columns, /list，没有区分实例。
        # 我们需要通过 header 传递 context_id (uid)
        # 修改 Vue 挂载代码，注入 window.nice_table_config 包含 uid
        
        ui.add_head_html(
            f"""
            <script>
            if (!document.getElementById('nice-table-style')) {{
                const link = document.createElement('link');
                link.id = 'nice-table-style';
                link.rel = 'stylesheet';
                link.href = '{css_url}';
                link.crossOrigin = 'anonymous';
                document.head.appendChild(link);
            }}
            window.__nice_table_registry = window.__nice_table_registry || {{}};
            </script>
            """
        )

        ui.html(f'<div id="{self.container_id}" style="width: 100%; height: 100%;"></div>').classes('w-full h-full')

        ui.add_body_html(
            f"""
            <script type="module">
            // 确保注册表存在
            window.__nice_table_registry = window.__nice_table_registry || {{}};
            // 预注册占位，防止 Python 早期调用报错
            if (!window.__nice_table_registry['{self.uid}']) {{
                window.__nice_table_registry['{self.uid}'] = {{
                    refreshData: () => console.log('NiceTable [' + '{self.uid}' + '] is initializing...'),
                    refreshColumns: () => {{}},
                    switchVersion: () => {{}}
                }};
            }}

            // 注入全局 Fetch 拦截器，自动附加 x-table-id
            if (!window.__nice_table_fetch_intercepted) {{
                window.__nice_table_fetch_intercepted = true;
                const originalFetch = window.fetch;
                window.fetch = function(url, options) {{
                    // 只拦截指向当前 API 的请求
                    if (typeof url === 'string' && (url.includes('/list') || url.includes('/columns') || url.includes('/filters') || url.includes('/row-') || url.includes('/add') || url.includes('/statistics'))) {{
                        options = options || {{}};
                        options.headers = options.headers || {{}};
                        
                        // 尝试从最近的 container 中查找 table-id
                        let tableId = null;
                        if (options.headers['x-table-id']) {{
                            tableId = options.headers['x-table-id'];
                        }}
                        
                        // 如果没有 tableId，不做处理，让 Axios 拦截器或其他逻辑处理
                    }}
                    return originalFetch(url, options);
                }};
            }}

            // 备用：轮询检查注册表（最多60次，30秒后停止）
            let pollCount = 0;
            const maxPolls = 60;
            const bindExpose = () => {{
                pollCount++;
                const registry = window.__nice_table_registry;
                const exposed = registry && registry['{self.uid}'];
                
                // 检查是否是真实实例（不仅仅是占位符）
                const isRealInstance = exposed && exposed.refreshData && !exposed.refreshData.toString().includes('initializing');

                if (isRealInstance) {{
                    console.log('NiceTable [' + '{self.uid}' + '] exposed instance found via polling (attempt ' + pollCount + ').');
                }} else if (pollCount < maxPolls) {{
                    setTimeout(bindExpose, 500);
                }} else {{
                    console.error('NiceTable [' + '{self.uid}' + '] exposed instance NOT found after 30s. JS module might have failed to load.');
                }}
            }};
            
            // 启动轮询
            bindExpose();

            const mountApp_{self.uid} = () => {{
                const container = document.getElementById('{self.container_id}');
                if (!container) {{
                    if (pollCount < 20) requestAnimationFrame(mountApp_{self.uid});
                    return;
                }}
                let root = container.querySelector('.nice-table-root');
                if (!root) {{
                    root = document.createElement('div');
                    root.className = 'nice-table-root';
                    root.style.width = '100%';
                    root.style.height = '100%';
                    container.appendChild(root);
                }}
                
                console.log('NiceTable [' + '{self.uid}' + '] starting to load JS module...');
                import('{js_url}')
                    .then((module) => {{
                        console.log('NiceTable [' + '{self.uid}' + '] JS module loaded, mounting...');
                        const mount = module.mountTable || window.mountNiceTable;
                        if (mount) {{
                            mount(root, {{
                                tableId: '{self.uid}',
                                defaultVersion: '{ "vxe" if self.use_vxe else "element" }',
                                apiUrl: ''
                            }});
                        }} else {{
                            console.error('NiceTable [' + '{self.uid}' + '] mountTable function not found in module');
                        }}
                    }})
                    .catch(err => {{
                        console.error('NiceTable [' + '{self.uid}' + '] failed to load JS module:', err);
                    }});
            }};

            mountApp_{self.uid}();
            </script>
            """
        )

    # ---------- API routes ----------
    @classmethod
    def _get_instance(cls, table_id: str) -> Optional['NiceTable']:
        return cls._instances.get(table_id)

    @classmethod
    def _ensure_routes(cls):
        if cls._router_registered:
            return

        router = APIRouter()

        def get_target_instance(request: Request) -> 'NiceTable':
            # 从 Header 中获取 table-id
            table_id = request.headers.get('x-table-id')
            if not table_id:
                # 兼容旧逻辑：如果只有一个实例，就返回那个
                # 如果有多个实例（如刷新页面后旧实例未销毁），返回最新创建的那个（字典的最后一个）
                if cls._instances:
                    return list(cls._instances.values())[-1]
                
                raise HTTPException(status_code=400, detail='缺少 x-table-id 请求头，且无可用实例')
            
            inst = cls._get_instance(table_id)
            if not inst:
                raise HTTPException(status_code=404, detail=f'Table instance {table_id} not found')
            return inst

        @router.post('/list')
        async def list_endpoint(request: Request, payload: Dict[str, Any]):
            inst = get_target_instance(request)
            filters = payload.get('filters')
            filter_params = FilterParams(**filters) if filters else None
            
            # 使用 to_thread 防止阻塞主循环
            return await asyncio.to_thread(
                inst.logic.get_list,
                filters=filter_params,
                page=payload.get('page', 1),
                page_size=payload.get('pageSize', inst.page_size),
                sort_by=payload.get('sortBy'),
                sort_order=payload.get('sortOrder'),
            )

        @router.post('/row-position')
        async def row_position(request: Request, payload: Dict[str, Any]):
            inst = get_target_instance(request)
            row_id = payload.get('row_id') or payload.get('rowId')
            if row_id is None:
                raise HTTPException(status_code=400, detail='缺少 rowId')
            filters = payload.get('filters')
            filter_params = FilterParams(**filters) if filters else None
            
            sort_by = payload.get('sortBy')
            sort_order = payload.get('sortOrder')
            
            data = await asyncio.to_thread(
                inst.logic.get_row_position,
                row_id, 
                filter_params,
                sort_by=sort_by,
                sort_order=sort_order
            )
            return {'success': True, 'data': data}

        @router.post('/row-detail')
        async def row_detail(request: Request, payload: Dict[str, Any]):
            inst = get_target_instance(request)
            row = payload.get('row') or {}
            row_id = row.get('id')
            if row_id is None:
                raise HTTPException(status_code=400, detail='缺少 row.id')
            data = await asyncio.to_thread(inst.logic.get_row_detail, row_id)
            return {'success': True, 'data': data}

        @router.get('/columns')
        async def columns(request: Request):
            # 增加重试逻辑
            for _ in range(10):
                try:
                    inst = get_target_instance(request)
                    return {'success': True, 'data': inst.logic.get_columns_config()}
                except (HTTPException, KeyError):
                    # 如果找不到实例，可能是刚创建，等待一下
                    await asyncio.sleep(0.2)
            
            # 最终尝试
            inst = get_target_instance(request)
            return {'success': True, 'data': inst.logic.get_columns_config()}

        @router.get('/filters')
        async def filter_options(request: Request):
            # 增加重试逻辑，确保在实例刚创建时能获取到选项
            for _ in range(10):
                try:
                    inst = get_target_instance(request)
                    options: Dict[str, List[str]] = {}
                    for col in inst.logic.columns_config:
                        if col.filterType not in {'select', 'multi-select'}:
                            continue
                        try:
                            # 从 col.options 获取（已在 add_data/update_dataframe 中更新）
                            if col.options:
                                 options[col.prop] = col.options
                            else:
                                 # 如果没有缓存的 options，尝试实时计算
                                 unique_values = inst.logic.dataframe[col.prop].dropna().unique()
                                 options[col.prop] = sorted([str(v) for v in unique_values])
                        except Exception:
                            options[col.prop] = []
                    return {'success': True, 'data': options}
                except (HTTPException, KeyError):
                    await asyncio.sleep(0.2)
            
            # 最终尝试
            try:
                inst = get_target_instance(request)
                return {'success': True, 'data': {}}
            except Exception:
                return {'success': False, 'data': {}, 'detail': 'Table instance not found'}

        @router.post('/add')
        async def add_data(request: Request, payload: Dict[str, Any]):
            inst = get_target_instance(request)
            data = payload.get('data')
            if not data:
                raise HTTPException(status_code=400, detail='缺少 data')
            result = inst.add_data(data, refresh=True)
            return {'success': True, 'data': result}

        @router.get('/statistics')
        async def statistics(request: Request):
            """获取数据统计信息（行列可扩展格式）"""
            inst = get_target_instance(request)
            statistics_data = inst.logic.get_statistics()
            return {'success': True, 'data': statistics_data}

        app.include_router(router)
        cls._router_registered = True


# 在应用启动前注册路由，确保 API 可用
NiceTable._ensure_routes()