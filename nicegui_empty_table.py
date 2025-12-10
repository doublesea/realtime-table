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
                
                # 列顺序测试按钮和显示
                with ui.row().classes('items-center gap-2'):
                    test_column_order_btn = ui.button('测试列顺序', icon='swap_vert').props('flat color=white size=sm')
                    show_order_btn = ui.button('显示列顺序', icon='list').props('flat color=white size=sm')
                column_order_info = ui.label('').classes('text-white text-xs max-w-md')

                auto_add_running = {'flag': False}
                timer_handle = {'instance': None}
                refresh_pending = {'count': 0}  # 用于防抖：累积刷新次数
                last_refresh_time = {'value': 0}  # 上次刷新时间
                initial_load = {'flag': True}  # 标记是否为初始加载阶段

                async def add_batch_data():
                    """定时添加一批数据到 DataFrame 并刷新表格（使用增量添加优化性能）"""
                    if not auto_add_running['flag']:
                        return
                    
                    # 生成一批数据
                    batch_size = 500
                    # 使用 asyncio.to_thread 避免阻塞主线程
                    try:
                        # 1. 生成数据 (CPU密集型)
                        new_records = await asyncio.to_thread(generate_batch_records, data_state['next_id'], batch_size)
                        data_state['next_id'] += batch_size
                        
                        # 2. 更新本地数据源 (CPU密集型 - pd.concat)
                        # 数据源完全由本文件管理
                        def update_local_df():
                            new_df = pd.DataFrame(new_records)
                            # 确保新数据中有 ID (虽然 generate_batch_records 会生成 id)
                            # 如果有特殊的列处理逻辑，可以在这里添加
                            return pd.concat([data_state['df_source'], new_df], ignore_index=True)
                            
                        data_state['df_source'] = await asyncio.to_thread(update_local_df)
                        
                    except Exception as e:
                        print(f"添加数据出错: {e}")
                        return
                    
                    # 更新状态显示
                    total_count = len(data_state['df_source'])
                    status_label.text = f'状态：运行中（已添加 {total_count} 条）'
                    
                    # 每10000行记录一次状态（用于调试）
                    if total_count % 10000 == 0:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"数据量达到 {total_count} 行")
                    
                    # 防抖机制：根据数据量调整刷新频率
                    current_time = time.time()
                    refresh_pending['count'] += 1
                    
                    # 初始加载阶段（前5000行）：每批都刷新，让用户看到过程
                    # 之后：每2批或超过0.8秒刷新一次，平衡性能和体验
                    should_refresh = False
                    if initial_load['flag'] and total_count < 5000:
                        should_refresh = True
                    else:
                        # 初始阶段结束
                        if initial_load['flag']:
                            initial_load['flag'] = False
                        # 正常阶段：每2批或超过0.8秒刷新一次
                        if refresh_pending['count'] >= 2 or (current_time - last_refresh_time['value']) >= 0.8:
                            should_refresh = True
                    
                    if should_refresh:
                        # 3. 只在需要刷新时，通知表格控件更新数据源
                        # 将最新的 DataFrame 传递给表格控件
                        # 使用 asyncio.to_thread 避免 update_dataframe 中的计算阻塞主线程
                        # 注意：update_dataframe 中包含了耗时的 unique() 计算
                        result = await asyncio.to_thread(table.logic.update_dataframe, data_state['df_source'])
                        if result.get('columns_updated'):
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

                async def test_column_order():
                    """测试列顺序：随机重排列顺序并验证是否正确"""
                    if data_state['df_source'].empty:
                        ui.notify('请先添加一些数据', type='warning')
                        return
                    
                    import random
                    
                    # 获取当前列顺序
                    current_columns = list(data_state['df_source'].columns)
                    original_order = current_columns.copy()
                    
                    # 随机重排列顺序（但保持 id 在第一位）
                    if 'id' in current_columns:
                        other_columns = [c for c in current_columns if c != 'id']
                        random.shuffle(other_columns)
                        new_order = ['id'] + other_columns
                    else:
                        random.shuffle(current_columns)
                        new_order = current_columns
                    
                    # 按照新顺序重新排列 DataFrame
                    def reorder_dataframe():
                        return data_state['df_source'][new_order].copy()
                    
                    # 更新 DataFrame（使用新顺序）
                    data_state['df_source'] = await asyncio.to_thread(reorder_dataframe)
                    
                    # 更新表格
                    result = await asyncio.to_thread(table.logic.update_dataframe, data_state['df_source'])
                    
                    # 获取更新后的列配置顺序
                    columns_config_result = table.logic.get_columns_config()
                    config_order = [col['prop'] for col in columns_config_result['columns']]
                    
                    # 验证列顺序
                    df_order = list(data_state['df_source'].columns)
                    is_correct = config_order == df_order
                    
                    # 显示结果
                    if is_correct:
                        column_order_info.text = f'✓ 列顺序正确: {", ".join(config_order[:5])}{"..." if len(config_order) > 5 else ""}'
                        column_order_info.classes('text-white text-xs')
                        ui.notify('列顺序测试通过！列顺序与 DataFrame 一致', type='positive')
                    else:
                        column_order_info.text = f'✗ 列顺序错误！期望: {df_order[:3]}..., 实际: {config_order[:3]}...'
                        column_order_info.classes('text-red-300 text-xs')
                        ui.notify(f'列顺序测试失败！期望: {df_order}, 实际: {config_order}', type='negative')
                    
                    # 刷新表格
                    if result.get('columns_updated'):
                        table.refresh_columns()
                    table.refresh_data()
                    
                    # 打印详细信息到控制台
                    print(f"\n{'='*60}")
                    print("列顺序测试结果:")
                    print(f"  原始顺序: {original_order}")
                    print(f"  新顺序:   {new_order}")
                    print(f"  DataFrame列顺序: {df_order}")
                    print(f"  配置列顺序:      {config_order}")
                    print(f"  是否一致: {'✓ 是' if is_correct else '✗ 否'}")
                    print(f"{'='*60}\n")
                
                test_column_order_btn.on('click', test_column_order)
                
                async def show_column_order():
                    """显示当前列顺序"""
                    if data_state['df_source'].empty:
                        ui.notify('表格为空，无列顺序信息', type='info')
                        return
                    
                    # 获取 DataFrame 的列顺序
                    df_order = list(data_state['df_source'].columns)
                    
                    # 获取配置的列顺序
                    columns_config_result = table.logic.get_columns_config()
                    config_order = [col['prop'] for col in columns_config_result['columns']]
                    
                    # 检查是否一致
                    is_consistent = df_order == config_order
                    
                    # 显示信息
                    order_text = f"列顺序: {', '.join(config_order[:8])}"
                    if len(config_order) > 8:
                        order_text += f" ... (共{len(config_order)}列)"
                    
                    if is_consistent:
                        column_order_info.text = f'✓ {order_text}'
                        column_order_info.classes('text-white text-xs max-w-md')
                        ui.notify(f'列顺序一致\nDataFrame: {df_order[:5]}...\n配置: {config_order[:5]}...', type='info', timeout=3000)
                    else:
                        column_order_info.text = f'✗ 列顺序不一致！\nDataFrame: {df_order[:5]}...\n配置: {config_order[:5]}...'
                        column_order_info.classes('text-red-300 text-xs max-w-md')
                        ui.notify(f'列顺序不一致！\nDataFrame: {df_order}\n配置: {config_order}', type='warning', timeout=5000)
                    
                    # 打印详细信息
                    print(f"\n{'='*60}")
                    print("当前列顺序:")
                    print(f"  DataFrame列顺序: {df_order}")
                    print(f"  配置列顺序:      {config_order}")
                    print(f"  是否一致: {'✓ 是' if is_consistent else '✗ 否'}")
                    print(f"{'='*60}\n")
                
                show_order_btn.on('click', show_column_order)

        with ui.card().classes('w-full flex-grow p-0 overflow-hidden'):
            table = NiceTable(dataframe=data_state['df_source'], columns_config=columns_config, page_size=100)


if __name__ in {"__main__", "__mp_main__"}:
    # 启动应用
    ui.run(title='NiceTable 演示 (指针)', port=8081, show=True)
