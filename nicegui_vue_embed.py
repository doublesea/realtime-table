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

# 导入后端API应用和数据初始化函数
from backend.api import app as fastapi_app, is_data_initialized, get_data_table, set_data_table, set_data_initialized
from backend.main import init_data
from backend.data_table import DataTable, generate_columns_config_from_dataframe

# 配置静态文件服务路径
dist_path = Path(__file__).parent / 'dist'

# FastAPI服务运行标志
_api_server_running = False
_api_server_thread = None


def run_fastapi_server():
    """在后台线程中运行FastAPI服务器"""
    global _api_server_running
    try:
        print("=" * 60)
        print("启动FastAPI后端服务...")
        print("=" * 60)
        uvicorn.run(fastapi_app, host="0.0.0.0", port=3001, log_level="info")
        _api_server_running = True
    except Exception as e:
        print(f"FastAPI服务启动失败: {e}")
        _api_server_running = False


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


if __name__ in {'__main__', '__mp_main__'}:
    print("=" * 60)
    print("大数据量表格系统 - 统一入口启动")
    print("=" * 60)
    
    # 1. 先初始化数据（在主线程中，确保完成）
    print("\n[1/3] 初始化数据...")
    try:
        data_df = init_data()
        print("✓ 数据生成完成")
        
        # 创建列配置
        print("创建列配置...")
        columns_config = generate_columns_config_from_dataframe(data_df)
        
        # 创建DataTable实例
        print("创建DataTable实例...")
        data_table = DataTable(dataframe=data_df, columns_config=columns_config)
        
        # 设置到API模块
        set_data_table(data_table)
        set_data_initialized(True)
        
        print(f"✓ DataTable实例创建完成，共 {len(data_df)} 条记录")
    except Exception as e:
        import traceback
        print(f"数据初始化失败: {e}")
        traceback.print_exc()
        raise
    
    # 2. 在后台线程启动FastAPI服务
    print("\n[2/3] 启动FastAPI后端服务...")
    _api_server_thread = threading.Thread(target=run_fastapi_server, daemon=True)
    _api_server_thread.start()
    
    # 等待一下确保FastAPI服务启动
    time.sleep(2)
    print("✓ FastAPI服务已启动")
    
    # 3. 配置NiceGUI静态文件和路由
    print("\n[3/3] 配置NiceGUI服务...")
    from nicegui import app as nicegui_app
    
    # 挂载静态文件（如果 dist 目录存在）
    if dist_path.exists():
        nicegui_app.mount("/static", StaticFiles(directory=str(dist_path), html=True), name="static")
        file_count = len(list(dist_path.rglob('*')))
        print(f"✓ Vue 应用已挂载，包含 {file_count} 个文件")
    else:
        print("⚠ Vue 应用未构建，请运行 'npm run build' 构建 Vue 应用")
    
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
            print(f"API代理错误: {e}")
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
    
    print("=" * 60)
    print("启动完成！")
    print("=" * 60)
    print("服务地址：")
    print("  - NiceGUI主页: http://localhost:8080/")
    print("  - 数据表格: http://localhost:8080/data-table")
    print("  - FastAPI后端: http://localhost:3001")
    print("  - API文档: http://localhost:3001/docs")
    print("=" * 60)
    
    # 4. 启动NiceGUI
    ui.run(title='大数据量表格系统', port=8080, show=True)
