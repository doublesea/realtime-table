"""NiceTable 集成演示：空表格 + 自动批量添加按钮"""

from __future__ import annotations

import asyncio
import time
import pandas as pd
from nicegui import ui

from data_generator import generate_single_record, generate_batch_records
from backend.data_table import generate_columns_config_from_dataframe
from nice_table import NiceTable


def create_empty_dataframe():
    """使用一条样本记录推断列结构，返回空 DataFrame 及列配置。"""
    sample = generate_single_record(1)
    df = pd.DataFrame([sample])
    if 'id' not in df.columns:
        df['id'] = 1
    df = df[['id'] + [c for c in df.columns if c != 'id']]
    columns_config = generate_columns_config_from_dataframe(df)
    return df.iloc[0:0], columns_config


@ui.page('/')
def main_page():
    ui.page_title('NiceTable 控件演示')
    ui.query('body').classes('overflow-hidden')

    # 创建数据源 DataFrame
    empty_df, columns_config = create_empty_dataframe()
    data_state = {
        'df_source': empty_df.copy(),
        'next_id': 1
    }

    # 页面布局
    with ui.column().classes('w-full h-screen p-4 gap-4 no-wrap'):
        with ui.row().classes('w-full items-center gap-4 flex-none justify-between bg-primary text-white px-4 py-2 rounded'):
            ui.label('NiceTable 空表格演示').classes('text-h6')
            
            with ui.row().classes('items-center gap-4'):
                status_label = ui.label('状态：未运行').classes('text-white')
                toggle_btn = ui.button('开始自动添加', icon='play_arrow').props('flat color=white')

                auto_add_running = {'flag': False}
                timer_handle = {'instance': None}
                refresh_pending = {'count': 0}  # 用于防抖：累积刷新次数
                last_refresh_time = {'value': 0}  # 上次刷新时间
                initial_load = {'flag': True}  # 标记是否为初始加载阶段

                def add_batch_data():
                    """定时添加一批数据到 DataFrame 并刷新表格（使用增量添加优化性能）"""
                    if not auto_add_running['flag']:
                        return
                    
                    # 生成一批数据
                    batch_size = 5000
                    new_records = generate_batch_records(data_state['next_id'], batch_size)
                    data_state['next_id'] += batch_size
                    
                    # 使用增量添加方法（性能优化：不会重建整个 DataTable）
                    result = table.add_data(new_records, refresh=False)
                    
                    # 更新状态显示（使用 DataTable 的总数）
                    total_count = table.logic.total_count
                    status_label.text = f'状态：运行中（已添加 {total_count} 条）'
                    
                    # 每1000行记录一次状态（用于调试）
                    if total_count % 1000 == 0:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"数据量达到 {total_count} 行，DataFrame长度={len(table.logic.dataframe)}")
                    
                    # 防抖机制：根据数据量调整刷新频率
                    current_time = time.time()
                    refresh_pending['count'] += 1
                    
                    # 初始加载阶段（前5000行）：每批都刷新，让用户看到过程
                    # 之后：每2批或超过0.8秒刷新一次，平衡性能和体验
                    if initial_load['flag'] and total_count < 5000:
                        # 初始阶段：每批都刷新
                        should_refresh = True
                    else:
                        # 初始阶段结束
                        if initial_load['flag']:
                            initial_load['flag'] = False
                        # 正常阶段：每2批或超过0.8秒刷新一次
                        should_refresh = (
                            refresh_pending['count'] >= 2 or  # 累积2批（1000行）
                            (current_time - last_refresh_time['value']) >= 0.8  # 或超过0.8秒
                        )
                    
                    if should_refresh:
                        # 检查列配置是否有变化
                        if result.get('columns_updated', False):
                            table.refresh_columns()
                        table.refresh_data()
                        refresh_pending['count'] = 0
                        last_refresh_time['value'] = current_time

                async def handle_toggle():
                    """切换自动添加状态"""
                    if auto_add_running['flag']:
                        # 停止
                        auto_add_running['flag'] = False
                        if timer_handle['instance']:
                            timer_handle['instance'].deactivate()
                        # 重置防抖计数器
                        refresh_pending['count'] = 0
                        last_refresh_time['value'] = 0
                        # 确保最后一次刷新
                        table.refresh_data()
                        status_label.text = '状态：未运行'
                        toggle_btn.text = '开始自动添加'
                        toggle_btn.props('flat color=white')
                        ui.notify('已停止自动添加', type='info')
                    else:
                        # 启动
                        auto_add_running['flag'] = True
                        initial_load['flag'] = True  # 重置初始加载标记
                        refresh_pending['count'] = 0  # 重置刷新计数器
                        last_refresh_time['value'] = time.time()  # 重置时间
                        timer_handle['instance'] = ui.timer(0.5, add_batch_data)
                        status_label.text = '状态：运行中（每0.5秒添加500条）'
                        toggle_btn.text = '停止自动添加'
                        toggle_btn.props('flat color=negative')
                        ui.notify('自动添加已启动', type='positive')

                toggle_btn.on('click', handle_toggle)

        with ui.card().classes('w-full flex-grow p-0 overflow-hidden'):
            table = NiceTable(dataframe=data_state['df_source'], columns_config=columns_config, page_size=100)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='空表格自动添加数据演示', port=8081, show=True)
