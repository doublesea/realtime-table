"""
NiceGUI 嵌入 Vue 应用
将已构建的 Vue 应用嵌入到 NiceGUI 页面中
"""
from nicegui import ui
from pathlib import Path
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from backend.main import app as fastapi_app, init_data

# 导入 data_df，可能是 None（延迟初始化）
from backend.main import data_df

# 数据初始化将在主程序启动时进行

# 配置静态文件服务路径
dist_path = Path(__file__).parent / 'dist'
# 静态文件挂载将在 NiceGUI app 启动时进行

@ui.page('/data-table')
def data_table_page():
    """大数据量表格页面 - 嵌入 Vue 应用"""
    ui.page_title('大数据量表格系统')
    
    # 检查 dist 目录是否存在
    if not dist_path.exists():
        with ui.card().classes('w-full p-8'):
            ui.label('Vue 应用未构建').classes('text-h4 text-red-500 mb-4')
            ui.label('请先运行以下命令构建 Vue 应用：').classes('text-body1 mb-2')
            ui.label('npm run build').classes('text-code bg-gray-100 p-2 rounded font-mono')
            ui.label('构建完成后刷新此页面').classes('text-body2 text-gray-600 mt-4')
            return
    
    # 使用 iframe 嵌入 Vue 应用
    # 这样可以完全隔离 Vue 应用的运行环境
    # 移除所有边距和内边距，确保全屏显示
    ui.add_head_html('''
        <style>
            body {
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
                width: 100% !important;
            }
            .nicegui-content {
                margin: 0 !important;
                padding: 0 !important;
                width: 100% !important;
                max-width: 100% !important;
            }
        </style>
    ''')
    
    ui.html(f'''
        <iframe 
            src="/static/index.html" 
            style="width: 100vw; height: 100vh; border: none; margin: 0; padding: 0; display: block; position: fixed; top: 0; left: 0;"
            frameborder="0"
            allowfullscreen
        ></iframe>
    ''', sanitize=False)

@ui.page('/')
def main_page():
    """主页面"""
    ui.page_title('大数据表格系统')
    
    with ui.column().classes('w-full items-center gap-4 p-8'):
        ui.label('大数据量表格系统').classes('text-h4 font-bold')
        ui.label('支持千万级数据展示、全局筛选、行选中保持等功能').classes('text-body1 text-gray-600')
        
        ui.separator().classes('w-full max-w-2xl')
        
        with ui.row().classes('gap-4'):
            ui.link('进入数据表格', '/data-table').classes('text-lg')
        
        with ui.card().classes('w-full max-w-2xl mt-8'):
            ui.label('功能特性').classes('text-h6 mb-4')
            with ui.column().classes('gap-2'):
                ui.label('✓ 支持10万条数据预生成和展示')
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

if __name__ in {'__main__', '__mp_main__'}:
    # 确保数据已初始化
    # 由于 init_data() 会修改全局变量，我们需要重新导入来获取更新后的值
    if data_df is None:
        print("正在初始化数据...")
        init_data()
        # 等待一下确保数据已经写入全局变量
        import time
        time.sleep(0.5)
        # 重新导入以获取最新的 data_df
        from backend.main import data_df as updated_data_df
        if updated_data_df is None:
            raise RuntimeError("数据初始化失败，请检查后端服务")
        # 使用更新后的 data_df
        data_df = updated_data_df
    
    # 验证数据已初始化
    if data_df is None:
        raise RuntimeError("数据未初始化，无法启动应用")
    
    print(f"数据初始化成功，共 {len(data_df)} 条记录")
    print(f"Vue 应用路径: {dist_path}")
    if dist_path.exists():
        file_count = len(list(dist_path.rglob('*')))
        print(f"✓ Vue 应用已构建，包含 {file_count} 个文件")
    else:
        print("⚠ Vue 应用未构建，请运行 'npm run build' 构建 Vue 应用")
    
    # 将 FastAPI 的路由集成到 NiceGUI 的 FastAPI 实例
    from nicegui import app as nicegui_app
    
    # 挂载静态文件（如果 dist 目录存在）
    if dist_path.exists():
        nicegui_app.mount("/static", StaticFiles(directory=str(dist_path), html=True), name="static")
    
    # 将 FastAPI 应用的路由添加到 NiceGUI 的 FastAPI 实例
    # NiceGUI 的 app 已经是 FastAPI 实例，可以直接添加路由
    for route in fastapi_app.routes:
        # 跳过已经存在的路由（避免重复）
        if any(r.path == route.path and set(r.methods or ['GET']) == set(route.methods or ['GET']) 
               for r in nicegui_app.routes if hasattr(r, 'path')):
            continue
        
        # 添加路由
        if hasattr(route, 'methods'):
            nicegui_app.add_api_route(
                route.path,
                route.endpoint,
                methods=list(route.methods),
                name=getattr(route, 'name', None)
            )
        else:
            nicegui_app.add_api_route(
                route.path,
                route.endpoint,
                methods=['GET'],
                name=getattr(route, 'name', None)
            )
    
    # 添加中间件（CORS 已经在 backend/main.py 中配置，但需要确保 NiceGUI 也支持）
    # 注意：NiceGUI 可能已经配置了 CORS，这里主要是确保 API 路由可以访问
    
    # 运行应用
    ui.run(title='大数据量表格系统', port=8080, show=False)

