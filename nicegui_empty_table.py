"""NiceTable 集成演示：空表格 + 自动批量添加按钮"""

from __future__ import annotations

import asyncio
import logging
import time
import pandas as pd
from nicegui import ui

from data_generator import generate_single_record, generate_batch_records
from data_table import generate_columns_config_from_dataframe
from nice_table import NiceTable

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_empty_dataframe():
    """使用一条样本记录推断列结构，返回空 DataFrame 及列配置。"""
    sample = generate_single_record(1)
    df = pd.DataFrame([sample])
    if 'id' not in df.columns:
        df['id'] = 1
    df = df[['id'] + [c for c in df.columns if c != 'id']]
    columns_config = generate_columns_config_from_dataframe(df)
    
    # 将 user_id 和 merchant 列设置为不支持筛选
    for col in columns_config:
        if col.prop in ['user_id', 'merchant']:
            col.filterable = False
        
        # 将 item_count 设置为多选筛选，测试数值类型的列表筛选
        if col.prop == 'item_count':
            col.filterType = 'multi-select'
            
    return df.iloc[0:0], columns_config


@ui.page('/')
def main_page():
    ui.page_title('NiceTable 大数据管理系统')
    ui.query('body').classes('overflow-hidden')
    
    # 核心修复：强力打通高度继承链条
    ui.add_head_html('''
        <style>
            /* 1. 基础容器：从页面到底部全部强制 100% */
            html, body, .q-layout, .q-page-container, .q-page { height: 100% !important; min-height: unset !important; }
            
            /* 2. NiceGUI 布局：确保 flex 容器能够撑开 */
            .q-page { display: flex !important; flex-direction: column !important; overflow: hidden !important; }
            
            /* 3. Tab 组件：这是最容易断裂的一环 */
            .q-tab-panels { flex-grow: 1 !important; display: flex !important; flex-direction: column !important; height: 100% !important; background: transparent !important; }
            .q-tab-panel { flex-grow: 1 !important; display: flex !important; flex-direction: column !important; padding: 0 !important; height: 100% !important; overflow: hidden !important; overflow: hidden !important; }
            
            /* 4. Card 与表格根容器 */
            .q-card { display: flex !important; flex-direction: column !important; flex-grow: 1 !important; }
            .nice-table-container { display: flex !important; flex-direction: column !important; flex-grow: 1 !important; height: 100% !important; min-height: 0 !important; }
            .nice-table-root { display: flex !important; flex-direction: column !important; flex-grow: 1 !important; height: 100% !important; min-height: 0 !important; }
        </style>
    ''')

    # 1. 初始化数据状态
    empty_df, columns_config = create_empty_dataframe()
    data_state = {
        'df_source': empty_df.copy(),
        'next_id': 1,
        'current_columns': list(empty_df.columns)
    }

    # 2. 布局：侧边栏 (Left Drawer)
    with ui.left_drawer(value=True, fixed=True).classes('bg-blue-50 border-r') as left_drawer:
        with ui.column().classes('w-full p-4 gap-4'):
            with ui.row().classes('items-center gap-2 mb-4'):
                ui.icon('settings', size='2rem').classes('text-primary')
                ui.label('控制面板').classes('text-h6 text-primary')
            
            ui.separator()
            
            ui.label('系统菜单').classes('text-xs font-bold text-grey-6 uppercase tracking-wider')
            with ui.column().classes('w-full gap-1'):
                ui.button('仪表盘', icon='dashboard').props('flat align=left').classes('w-full justify-start')
                ui.button('实时数据', icon='bolt').props('flat align=left').classes('w-full justify-start text-primary bg-blue-100')
                ui.button('历史记录', icon='history').props('flat align=left').classes('w-full justify-start')
                ui.button('数据导出', icon='download').props('flat align=left').classes('w-full justify-start')
            
            ui.separator().classes('my-4')
            
            ui.label('快速设置').classes('text-xs font-bold text-grey-6 uppercase tracking-wider')
            with ui.card().classes('w-full p-3 bg-white shadow-none border'):
                ui.label('表格引擎').classes('text-xs text-grey-7 mb-1')
                version_select = ui.select(
                    {'vxe': 'VXETable (高性能)', 'element': 'Element Plus'},
                    value='vxe'
                ).props('dense outlined').classes('w-full')
                
                ui.label('数据模拟').classes('text-xs text-grey-7 mt-3 mb-1')
                toggle_btn = ui.button('开始自动添加', icon='play_arrow').classes('w-full')

    # 3. 布局：页脚 (Footer)
    with ui.footer().classes('bg-white text-dark border-t'):
        with ui.row().classes('w-full justify-between px-4 py-1 items-center'):
            with ui.row().classes('items-center gap-4'):
                ui.label('NiceTable © 2026').classes('text-xs text-grey-6')
                ui.separator().props('vertical')
                status_label = ui.label('状态：未运行').classes('text-xs text-grey-7')
            
            with ui.row().classes('items-center gap-2'):
                ui.icon('circle', size='8px').classes('text-green-500')
                ui.label('系统在线').classes('text-xs text-grey-6')
                ui.label('v1.2.0').classes('text-xs text-grey-4 ml-2')

    # 4. 布局：顶部标题栏 (Header)
    with ui.header().classes('items-center justify-between bg-primary text-white px-4'):
        with ui.row().classes('items-center gap-4'):
            ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
            ui.label('大数据管理').classes('text-h6 font-bold tracking-tight')
        
        # 将 Tab 切换放在 Header 中间
        with ui.tabs().classes('bg-primary') as tabs:
            ui.tab('表格视图', icon='grid_on')
            ui.tab('统计分析', icon='analytics')
        
        with ui.row().classes('items-center gap-3'):
            ui.button(icon='notifications').props('flat round color=white')
            ui.avatar('person', color='white', text_color='primary').classes('cursor-pointer')

    # 5. 布局：主内容区域 (Main Content)
    with ui.column().classes('w-full h-full p-4 gap-4 no-wrap'):
        # 顶层工具条
        with ui.row().classes('w-full items-center gap-2 flex-none justify-start bg-grey-1 p-2 rounded border'):
            test_column_order_btn = ui.button('测试列顺序', icon='swap_vert').props('outline size=sm')
            show_order_btn = ui.button('显示列顺序', icon='list').props('outline size=sm')
            switch_col_btn = ui.button('切换列配置', icon='settings_suggest').props('outline size=sm')
            
            ui.separator().props('vertical').classes('mx-2')
            column_order_info = ui.label('就绪').classes('text-grey-7 text-xs italic')

        # 使用 Header 中定义的 tabs，初始设置为 '统计分析'
        with ui.tab_panels(tabs, value='统计分析').classes('w-full flex-grow bg-transparent'):
            with ui.tab_panel('表格视图').classes('p-0'):
                with ui.card().classes('w-full h-full p-0 overflow-hidden shadow-none border-none'):
                    table = NiceTable(dataframe=data_state['df_source'], columns_config=columns_config, page_size=200, use_vxe=True)
            
            with ui.tab_panel('统计分析'):
                with ui.card().classes('w-full p-6 shadow-sm border'):
                    ui.label('这里可以放置统计图表或其他分析内容').classes('text-h6 mb-4')
                    ui.label('当前数据总量: ').bind_text_from(data_state, 'df_source', backward=lambda df: f"{len(df):,} 条记录")

    # --- 6. 逻辑控制与事件定义 ---

    auto_add_running = {'flag': False}
    timer_handle = {'instance': None}
    refresh_pending = {'count': 0}
    last_refresh_time = {'value': 0}
    initial_load = {'flag': True}

    async def add_batch_data():
        if not auto_add_running['flag']:
            return
        
        batch_size = 500
        try:
            new_records = await asyncio.to_thread(generate_batch_records, data_state['next_id'], batch_size)
            data_state['next_id'] += batch_size
            
            def update_local_df():
                new_df = pd.DataFrame(new_records)
                current_cols = data_state['current_columns']
                for col in current_cols:
                    if col not in new_df.columns:
                        if col == 'remark': new_df[col] = '自动补齐'
                        elif col == 'is_priority': new_df[col] = False
                        else: new_df[col] = None
                return pd.concat([data_state['df_source'], new_df[current_cols]], ignore_index=True)
                
            data_state['df_source'] = await asyncio.to_thread(update_local_df)
        except Exception as e:
            logger.error(f"添加数据出错: {e}")
            return
        
        total_count = len(data_state['df_source'])
        status_label.text = f'状态：运行中（已添加 {total_count} 条）'
        
        current_time = time.time()
        refresh_pending['count'] += 1
        
        should_refresh = False
        if initial_load['flag'] and total_count < 5000:
            should_refresh = True
        else:
            if initial_load['flag']: initial_load['flag'] = False
            if refresh_pending['count'] >= 2 or (current_time - last_refresh_time['value']) >= 0.8:
                should_refresh = True
        
        if should_refresh:
            result = await asyncio.to_thread(table.logic.update_dataframe, data_state['df_source'])
            if result.get('structure_updated'):
                table.refresh_columns()
            table.refresh_data()
            refresh_pending['count'] = 0
            last_refresh_time['value'] = current_time

    async def handle_toggle():
        if auto_add_running['flag']:
            auto_add_running['flag'] = False
            if timer_handle['instance']:
                timer_handle['instance'].deactivate()
            status_label.text = '状态：未运行'
            toggle_btn.text = '开始自动添加'
            toggle_btn.props('color=primary')
            ui.notify('已停止自动添加', type='info')
        else:
            auto_add_running['flag'] = True
            initial_load['flag'] = True
            timer_handle['instance'] = ui.timer(0.5, add_batch_data)
            status_label.text = '状态：运行中（每0.5秒添加500条）'
            toggle_btn.text = '停止自动添加'
            toggle_btn.props('color=negative')
            ui.notify('自动添加已启动', type='positive')

    async def test_column_order():
        if data_state['df_source'].empty:
            ui.notify('请先添加一些数据', type='warning')
            return
        import random
        cols = list(data_state['df_source'].columns)
        if 'id' in cols:
            other = [c for c in cols if c != 'id']
            random.shuffle(other)
            new_order = ['id'] + other
        else:
            random.shuffle(cols)
            new_order = cols
        
        data_state['df_source'] = data_state['df_source'][new_order].copy()
        result = await asyncio.to_thread(table.logic.update_dataframe, data_state['df_source'])
        if result.get('structure_updated'):
            table.refresh_columns()
        table.refresh_data()
        await show_column_order()
        ui.notify('列顺序已随机打乱并同步', type='positive')

    async def show_column_order():
        if data_state['df_source'].empty:
            column_order_info.text = '表格为空'
            return
        df_order = list(data_state['df_source'].columns)
        config_order = [col['prop'] for col in table.logic.get_columns_config()['columns']]
        if df_order == config_order:
            column_order_info.text = f'✓ 顺序正确: {", ".join(df_order[:3])}...'
        else:
            column_order_info.text = '✗ 顺序不一致！'

    async def switch_columns():
        current = data_state['current_columns']
        if 'remark' not in current:
            new_cols = [c for c in current if c not in ['payment_method', 'item_count']]
            if 'id' in new_cols:
                idx = new_cols.index('id') + 1
                new_cols[idx:idx] = ['remark', 'is_priority']
            else:
                new_cols.extend(['remark', 'is_priority'])
            ui.notify('切换到增强配置 (增加备注/优先级)', type='info')
        else:
            _, config = create_empty_dataframe()
            new_cols = [c.prop for c in config]
            ui.notify('恢复原始列配置', type='info')
        
        data_state['current_columns'] = new_cols
        def update_struct(df, target):
            if df.empty: return pd.DataFrame(columns=target)
            for c in target:
                if c not in df.columns:
                    df[c] = '切配置生成' if c == 'remark' else (False if c == 'is_priority' else None)
            return df[target].copy()
        
        data_state['df_source'] = await asyncio.to_thread(update_struct, data_state['df_source'], new_cols)
        result = await asyncio.to_thread(table.logic.update_dataframe, data_state['df_source'])
        if result.get('structure_updated'):
            table.refresh_columns()
        table.refresh_data()
        await show_column_order()

    # 绑定回调
    toggle_btn.on_click(handle_toggle)
    version_select.on_value_change(lambda e: table.switch_version(e.value))
    test_column_order_btn.on_click(test_column_order)
    show_order_btn.on_click(show_column_order)
    switch_col_btn.on_click(switch_columns)


if __name__ in {"__main__", "__mp_main__"}:
    # 启动应用
    ui.run(title='NiceTable 演示 (指针)', port=8081, show=True)
