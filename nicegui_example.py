"""
NiceGUI 表格组件使用示例
演示如何将 DataTablePage 集成到现有的 NiceGUI 应用中
"""
# 应用兼容性修复（如果需要）
try:
    import nicegui_fix
except ImportError:
    pass

from nicegui import ui
from nicegui_table import DataTablePage
from backend.main import init_data, data_df
import pandas as pd


@ui.page('/data-table')
def data_table_page():
    """大数据量表格页面"""
    # 确保数据已初始化
    from backend.main import data_df as backend_data_df, init_data
    
    # 如果数据未初始化，先初始化
    if backend_data_df is None:
        init_data()
        # 重新导入以确保获取最新值
        from backend.main import data_df as backend_data_df
    
    # 验证数据不为空
    if backend_data_df is None:
        ui.notify('数据初始化失败，请检查后端服务', type='error')
        return
    
    # 创建表格页面
    table_page = DataTablePage(backend_data_df)
    table_page.create_page()


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


if __name__ in {'__main__', '__mp_main__'}: 
    # 初始化数据（确保在应用启动前完成）
    from backend.main import init_data, data_df
    
    # 如果数据未初始化，先初始化
    if data_df is None:
        init_data()
    
    # 验证数据已初始化
    from backend.main import data_df as final_data_df
    if final_data_df is None:
        print("错误：数据初始化失败")
        exit(1)
    
    print(f"数据初始化成功，共 {len(final_data_df)} 条记录")
    
    # 运行应用
    ui.run(title='大数据量表格系统', port=8080, show=False)

