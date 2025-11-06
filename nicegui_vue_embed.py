"""
NiceGUI 嵌入 Vue 应用
将已构建的 Vue 应用嵌入到 NiceGUI 页面中
统一入口：启动后端服务（FastAPI）和前端服务（NiceGUI）
"""
from nicegui import ui
from pathlib import Path
import os
import threading
import time
import uvicorn
from fastapi.staticfiles import StaticFiles
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 导入后端API应用和数据初始化函数
from backend.api import app as fastapi_app, is_data_initialized, get_data_table, set_data_table, set_data_initialized
from backend.main import init_data
from backend.data_table import DataTable, generate_columns_config_from_dataframe

# 配置静态文件服务路径
dist_path = Path(__file__).parent / 'dist'

# FastAPI服务运行标志
_api_server_running = False
_api_server_thread = None


def check_port_available(port: int) -> bool:
    """检查端口是否可用"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            return result != 0  # 0 表示端口被占用
    except Exception:
        return True


def run_fastapi_server():
    """在后台线程中运行FastAPI服务器"""
    global _api_server_running
    try:
        logger.info("启动FastAPI后端服务...")
        # 检查端口是否已被占用
        if not check_port_available(3001):
            logger.warning("端口 3001 已被占用，可能已有服务在运行")
            _api_server_running = False
            return
        
        uvicorn.run(fastapi_app, host="0.0.0.0", port=3001, log_level="info")
        _api_server_running = True
    except OSError as e:
        if "10048" in str(e) or "Address already in use" in str(e):
            logger.warning("端口 3001 已被占用，可能已有 FastAPI 服务在运行")
        else:
            logger.error(f"FastAPI服务启动失败: {e}", exc_info=True)
        _api_server_running = False
    except Exception as e:
        logger.error(f"FastAPI服务启动失败: {e}", exc_info=True)
        _api_server_running = False


def create_data_table_widget(container_id: str = 'root'):
    """创建数据表格控件（作为 NiceGUI 控件）
    
    Args:
        container_id: Vue 应用挂载容器的 ID，默认为 'root'
    """
    # 检查 dist 目录是否存在
    if not dist_path.exists():
        with ui.card().classes('w-full p-8'):
            ui.label('Vue 应用未构建').classes('text-h4 text-red-500 mb-4')
            ui.label('请先运行以下命令构建 Vue 应用：').classes('text-body1 mb-2')
            ui.label('npm run build').classes('text-code bg-gray-100 p-2 rounded font-mono')
            ui.label('构建完成后刷新此页面').classes('text-body2 text-gray-600 mt-4')
        return
    
    # 读取构建后的 HTML 文件，提取资源路径
    index_html_path = dist_path / 'index.html'
    css_path = None
    js_path = None
    
    if index_html_path.exists():
        with open(index_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 提取 CSS 和 JS 路径
        import re
        css_match = re.search(r'href="([^"]+\.css)"', html_content)
        js_match = re.search(r'src="([^"]+\.js)"', html_content)
        
        if css_match:
            css_path = css_match.group(1)
            # 确保路径以 / 开头
            if not css_path.startswith('/'):
                css_path = '/' + css_path.lstrip('/')
        
        if js_match:
            js_path = js_match.group(1)
            # 确保路径以 / 开头
            if not js_path.startswith('/'):
                js_path = '/' + js_path.lstrip('/')
    
    # 如果无法从 HTML 中提取，尝试查找文件
    if not css_path:
        # 查找 dist/assets 目录下的 CSS 文件
        assets_dir = dist_path / 'assets'
        if assets_dir.exists():
            css_files = list(assets_dir.glob('*.css'))
            if css_files:
                css_path = f'/static/assets/{css_files[0].name}'
    
    if not js_path:
        # 查找 dist/assets 目录下的 JS 文件
        assets_dir = dist_path / 'assets'
        if assets_dir.exists():
            js_files = list(assets_dir.glob('*.js'))
            if js_files:
                js_path = f'/static/assets/{js_files[0].name}'
    
    # 添加 CSS 样式（只在第一次加载时添加）
    if css_path:
        # 检查是否已经添加过 CSS，避免重复加载
        ui.add_head_html(f'''
            <script>
                if (!document.getElementById('vue-table-css')) {{
                    const link = document.createElement('link');
                    link.rel = 'stylesheet';
                    link.crossOrigin = 'anonymous';
                    link.href = '{css_path}';
                    link.id = 'vue-table-css';
                    document.head.appendChild(link);
                }}
            </script>
        ''')
    
    # 添加自定义样式，确保表格控件正确显示
    ui.add_head_html(f'''
        <style>
            #{container_id} {{
                width: 100%;
                height: 100%;
                min-height: 600px;
            }}
            /* 确保 Element Plus 样式正确应用 */
            .nicegui-content {{
                overflow: visible !important;
            }}
            /* 确保表格容器占满可用空间 */
            .table-card {{
                height: calc(100vh - 250px);
            }}
            /* 确保 tab panel 中的容器正确显示 */
            .q-panel {{
                height: 100%;
            }}
        </style>
    ''')
    
    # 创建 Vue 应用挂载容器
    container = ui.html(f'''
        <div id="{container_id}" style="width: 100%; height: 100%;"></div>
    ''', sanitize=False).classes('w-full').style('height: calc(100vh - 250px); min-height: 600px;')
    
    # 加载 Vue 应用的 JavaScript
    # 使用 ui.add_body_html 确保脚本在 DOM 加载后执行
    if js_path:
        # 生成唯一的脚本 ID，避免重复加载
        script_id = f'vue-table-script-{container_id}'
        ui.add_body_html(f'''
            <script type="module" crossorigin id="{script_id}">
                // 等待容器出现并加载 Vue 应用
                function loadVueApp() {{
                    const container = document.getElementById('{container_id}');
                    if (!container) {{
                        // 容器还未渲染（可能在隐藏的 tab 中），稍后重试
                        setTimeout(loadVueApp, 200);
                        return;
                    }}
                    
                    // 检查容器是否可见（tab 切换时可能隐藏）
                    if (container.offsetParent === null) {{
                        // 容器存在但不可见，可能是 tab 未激活，稍后重试
                        setTimeout(loadVueApp, 200);
                        return;
                    }}
                    
                    // 检查是否已经加载过
                    if (window.vueAppLoaded_{container_id}) {{
                        console.log('Vue app already loaded for {container_id}');
                        return;
                    }}
                    
                    // 标记正在加载
                    window.vueAppLoading_{container_id} = true;
                    
                    // 加载 Vue 应用
                    import('{js_path}').then(() => {{
                        // Vue 应用已经挂载到 #root（由 main.ts 自动完成）
                        window.vueAppLoaded_{container_id} = true;
                        console.log('Vue app loaded for {container_id}');
                    }}).catch(err => {{
                        console.error('Failed to load Vue application:', err);
                        if (container) {{
                            container.innerHTML = '<div style="padding: 20px; color: red;">加载 Vue 应用失败: ' + err.message + '</div>';
                        }}
                        window.vueAppLoading_{container_id} = false;
                    }});
                }}
                
                // 使用 MutationObserver 监听容器出现（适用于 tab 懒加载）
                let observer = null;
                
                function startObserver() {{
                    if (observer) return;
                    
                    observer = new MutationObserver(() => {{
                        const container = document.getElementById('{container_id}');
                        if (container && container.offsetParent !== null) {{
                            // 容器已出现且可见
                            if (!window.vueAppLoaded_{container_id} && !window.vueAppLoading_{container_id}) {{
                                loadVueApp();
                            }}
                        }}
                    }});
                    
                    if (document.body) {{
                        observer.observe(document.body, {{
                            childList: true,
                            subtree: true
                        }});
                        // 立即尝试加载（如果容器已经存在）
                        loadVueApp();
                    }} else {{
                        document.addEventListener('DOMContentLoaded', () => {{
                            observer.observe(document.body, {{
                                childList: true,
                                subtree: true
                            }});
                            loadVueApp();
                        }});
                    }}
                }}
                
                // 如果容器ID是 'root'，直接加载；否则等待容器出现
                if ('{container_id}' === 'root') {{
                    // 等待 DOM 加载完成
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', loadVueApp);
                    }} else {{
                        loadVueApp();
                    }}
                }} else {{
                    // 对于非 root 容器，使用观察者模式
                    startObserver();
                }}
            </script>
        ''')
    else:
        # 如果找不到 JS 文件，显示错误信息
        with ui.card().classes('w-full p-8'):
            ui.label('无法加载 Vue 应用脚本文件').classes('text-red-500')
            ui.label('请检查 dist/assets 目录是否存在构建后的 JavaScript 文件').classes('text-body2 text-gray-600 mt-2')
    
    return container


@ui.page('/data-table')
def data_table_page():
    """大数据量表格页面 - 作为控件嵌入（保留原有路由）"""
    ui.page_title('大数据量表格系统')
    create_data_table_widget('root')


@ui.page('/')
def main_page():
    """主页面 - 使用 Tab 组件"""
    ui.page_title('大数据表格系统')
    
    # 使用 Tab 组件
    with ui.tabs().classes('w-full') as tabs:
        home_tab = ui.tab('首页', icon='home')
        table_tab = ui.tab('数据表格', icon='table_chart')
    
    with ui.tab_panels(tabs, value=home_tab).classes('w-full'):
        # 首页 Tab
        with ui.tab_panel(home_tab):
            with ui.column().classes('w-full items-center gap-4 p-8'):
                ui.label('大数据量表格系统').classes('text-h4 font-bold')
                ui.label('支持千万级数据展示、全局筛选、行选中保持等功能').classes('text-body1 text-gray-600')
                
                ui.separator().classes('w-full max-w-2xl')
                
                # 显示服务状态
                with ui.card().classes('w-full max-w-2xl mt-4'):
                    ui.label('服务状态').classes('text-h6 mb-4')
                    with ui.column().classes('gap-2'):
                        data_table = get_data_table()
                        if data_table:
                            ui.label(f'✓ 后端服务运行中 (端口: 3001)').classes('text-green-600')
                            ui.label(f'✓ 数据已加载，共 {len(data_table.dataframe)} 条记录').classes('text-green-600')
                        else:
                            ui.label('⚠ 后端服务正在初始化...').classes('text-yellow-600')
                        
                        if dist_path.exists():
                            ui.label('✓ Vue 应用已构建').classes('text-green-600')
                        else:
                            ui.label('⚠ Vue 应用未构建').classes('text-yellow-600')
                
                with ui.card().classes('w-full max-w-2xl mt-8'):
                    ui.label('功能特性').classes('text-h6 mb-4')
                    with ui.column().classes('gap-2'):
                        ui.label('✓ 支持1000万条数据预生成和展示')
                        ui.label('✓ 服务端分页，每页可调整（50/100/200/500）')
                        ui.label('✓ 全局筛选功能（文本、数字、下拉、日期）')
                        ui.label('✓ 支持多条件组合筛选（AND/OR逻辑）')
                        ui.label('✓ 行展开详情功能')
                        ui.label('✓ 行选中保持可见功能')
                        ui.label('✓ 列隐藏设置功能')
                        ui.label('✓ 文本类型唯一值列表筛选（<100时）')
                
                with ui.card().classes('w-full max-w-2xl mt-4'):
                    ui.label('技术架构').classes('text-h6 mb-4')
                    with ui.column().classes('gap-2'):
                        ui.label('• 前端：Vue 3 + Element Plus + TypeScript')
                        ui.label('• 后端：FastAPI + Pandas + NumPy')
                        ui.label('• 框架：NiceGUI（嵌入 Vue 应用）')
                        ui.label('• 数据存储：Pandas DataFrame（内存）')
                        ui.label('• API服务：http://localhost:3001')
                        ui.label('• 前端服务：http://localhost:8080')
        
        # 数据表格 Tab
        with ui.tab_panel(table_tab):
            # 先获取 js_path，以便在 tab 切换时使用
            index_html_path = dist_path / 'index.html'
            js_path_for_tab = None
            if index_html_path.exists():
                with open(index_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                import re
                js_match = re.search(r'src="([^"]+\.js)"', html_content)
                if js_match:
                    js_path_for_tab = js_match.group(1)
                    if not js_path_for_tab.startswith('/'):
                        js_path_for_tab = '/' + js_path_for_tab.lstrip('/')
            
            if not js_path_for_tab:
                assets_dir = dist_path / 'assets'
                if assets_dir.exists():
                    js_files = list(assets_dir.glob('*.js'))
                    if js_files:
                        js_path_for_tab = f'/static/assets/{js_files[0].name}'
            
            # 监听 tab 切换事件
            def on_tab_change(e):
                # 当切换到表格 tab 时，检查并加载 Vue 应用
                if js_path_for_tab:
                    ui.run_javascript(f'''
                        setTimeout(() => {{
                            const container = document.getElementById('root');
                            if (container && !window.vueAppLoaded_root && !window.vueAppLoading_root) {{
                                console.log('Tab switched to table, loading Vue app...');
                                window.vueAppLoading_root = true;
                                import('{js_path_for_tab}').then(() => {{
                                    window.vueAppLoaded_root = true;
                                    window.vueAppLoading_root = false;
                                    console.log('Vue app loaded after tab switch');
                                }}).catch(err => {{
                                    console.error('Failed to load Vue app:', err);
                                    window.vueAppLoading_root = false;
                                }});
                            }}
                        }}, 100);
                    ''')
            
            tabs.on('update:model-value', lambda e: on_tab_change(e))
            create_data_table_widget('root')


if __name__ in {'__main__', '__mp_main__'}:
    logger.info("=" * 60)
    logger.info("大数据量表格系统 - 统一入口启动")
    logger.info("=" * 60)
    
    # 1. 先初始化数据（在主线程中，确保完成）
    logger.info("\n[1/3] 初始化数据...")
    try:
        data_df = init_data()
        logger.info("✓ 数据生成完成")
        
        # 创建列配置
        logger.info("创建列配置...")
        columns_config = generate_columns_config_from_dataframe(data_df)
        
        # 创建DataTable实例
        logger.info("创建DataTable实例...")
        data_table = DataTable(dataframe=data_df, columns_config=columns_config)
        
        # 设置到API模块
        set_data_table(data_table)
        set_data_initialized(True)
        logger.info(f"✓ DataTable实例创建完成，共 {len(data_df)} 条记录")
    except Exception as e:
        logger.error(f"数据初始化失败: {e}", exc_info=True)
        raise
    
    # 2. 在后台线程启动FastAPI服务
    logger.info("\n[2/3] 启动FastAPI后端服务...")
    # 检查是否已有服务在运行
    if not check_port_available(3001):
        logger.info("⚠ 检测到端口 3001 已被占用")
        logger.info("   假设已有 FastAPI 服务在运行，跳过启动")
    else:
        _api_server_thread = threading.Thread(target=run_fastapi_server, daemon=True)
        _api_server_thread.start()
        
        # 等待一下确保FastAPI服务启动
        time.sleep(2)
        
        # 再次检查服务是否成功启动
        if check_port_available(3001):
            logger.warning("⚠ 警告: FastAPI服务可能启动失败，请检查日志")
        else:
            logger.info("✓ FastAPI服务已启动")
    
    # 3. 配置NiceGUI静态文件和路由
    logger.info("\n[3/3] 配置NiceGUI服务...")
    from nicegui import app as nicegui_app
    
    # 挂载静态文件（如果 dist 目录存在）
    if dist_path.exists():
        nicegui_app.mount("/static", StaticFiles(directory=str(dist_path), html=True), name="static")
        file_count = len(list(dist_path.rglob('*')))
        logger.info(f"✓ Vue 应用已挂载，包含 {file_count} 个文件")
    else:
        logger.warning("⚠ Vue 应用未构建，请运行 'npm run build' 构建 Vue 应用")
    
    # 添加API代理：将 /api/* 请求转发到 FastAPI 服务
    import httpx
    from fastapi import Request
    from fastapi.responses import Response
    
    @nicegui_app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
    async def proxy_api(request: Request, path: str):
        """代理API请求到FastAPI后端服务"""
        try:
            # 构建目标URL
            url = f"http://localhost:3001/api/{path}"
            
            # 获取请求参数
            params = dict(request.query_params)
            
            # 获取请求体
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            # 获取请求头（排除host和content-length）
            headers = dict(request.headers)
            headers.pop("host", None)
            headers.pop("content-length", None)
            
            # 发送请求到FastAPI服务
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=request.method,
                    url=url,
                    params=params,
                    content=body,
                    headers=headers
                )
                
                # 返回响应
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
        except Exception as e:
            logger.error(f"API代理错误: {e}", exc_info=True)
            return Response(
                content=f'{{"error": "代理请求失败: {str(e)}"}}',
                status_code=500,
                media_type="application/json"
            )
    
    @nicegui_app.get("/api/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "ok",
            "backend": "http://localhost:3001",
            "data_initialized": is_data_initialized()
        }
    
    logger.info("=" * 60)
    logger.info("启动完成！")
    logger.info("=" * 60)
    logger.info("服务地址：")
    logger.info("  - NiceGUI主页: http://localhost:8080/")
    logger.info("  - 数据表格: http://localhost:8080/data-table")
    logger.info("  - FastAPI后端: http://localhost:3001")
    logger.info("  - API文档: http://localhost:3001/docs")
    logger.info("=" * 60)
    
    # 4. 启动NiceGUI
    ui.run(title='大数据量表格系统', port=8080, show=True)
