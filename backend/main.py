"""程序入口 - 生成数据并启动应用

负责：
1. 生成数据
2. 创建DataTable实例
3. 启动FastAPI应用
"""

from datetime import datetime, timedelta
import random
import asyncio
import threading
import pandas as pd
import numpy as np

try:
    from .data_table import DataTable, generate_columns_config_from_dataframe
    from .api import app, set_data_table, set_data_initialized, is_data_initialized
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from backend.data_table import DataTable, generate_columns_config_from_dataframe
    from backend.api import app, set_data_table, set_data_initialized, is_data_initialized

# 数据生成配置
TOTAL_RECORDS = 100000


def init_data() -> pd.DataFrame:
    """初始化数据，生成指定数量的数据并保存到DataFrame（优化版本）"""
    print(f"开始生成 {TOTAL_RECORDS} 条数据...")
    start_time = datetime.now()
    departments = ['技术部', '销售部', '市场部', '人事部', '财务部']
    statuses = ['在职', '离职', '试用期']
    
    # 使用向量化操作高效生成数据
    ids = np.arange(1, TOTAL_RECORDS + 1, dtype=np.int64)
    
    # 使用numpy的随机数生成（基于ID作为种子，确保可重复）
    # 为了确保可重复性，我们使用ID作为随机种子
    np.random.seed(42)  # 固定种子，保证整体可重复
    
    # 生成年龄（18-68）
    ages = np.random.randint(18, 69, size=TOTAL_RECORDS)
    
    # 生成薪资（10000-60000）
    salaries = np.random.randint(10000, 60001, size=TOTAL_RECORDS)
    
    # 生成部门（使用ID作为索引确保可重复）
    dept_indices = (ids - 1) % len(departments)
    dept_values = np.array(departments)[dept_indices]
    
    # 生成状态（使用ID作为索引确保可重复）
    status_indices = (ids * 3) % len(statuses)
    status_values = np.array(statuses)[status_indices]
    
    # 生成日期偏移（0-365天）
    day_offsets = np.random.randint(0, 366, size=TOTAL_RECORDS)
    base_date = datetime.now()
    # 使用列表推导式生成日期字符串（这部分无法完全向量化，但已经很快）
    create_times = [(base_date - timedelta(days=int(offset))).strftime('%Y-%m-%d') for offset in day_offsets]
    
    # 生成姓名和邮箱（使用列表推导式，已经很高效）
    names = [f"用户_{str(id).zfill(8)}" for id in ids]
    emails = [f"user{id}@example.com" for id in ids]
    
    # 创建DataFrame（使用字典方式，更高效）
    data_df = pd.DataFrame({
        'id': ids,
        'name': names,
        'email': emails,
        'age': ages,
        'department': dept_values,
        'salary': salaries,
        'status': status_values,
        'createTime': create_times
    })
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"数据生成完成，共 {len(data_df)} 条记录，总耗时: {elapsed:.2f}秒")
    print(f"数据预览:\n{data_df.head()}")
    
    return data_df


# 全局变量用于线程间通信
_data_df = None
_data_ready = threading.Event()


def _init_data_thread():
    """在后台线程中初始化数据"""
    global _data_df
    _data_df = init_data()
    _data_ready.set()


# 应用启动时初始化数据
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据（如果数据已初始化则跳过）"""
    # 检查数据是否已经初始化（例如在nicegui_vue_embed.py中已初始化）
    if is_data_initialized():
        print("=" * 60)
        print("数据已在外部初始化，跳过startup_event中的初始化")
        print("=" * 60)
        return
    
    print("=" * 60)
    print("开始初始化数据...")
    print("=" * 60)
    
    # 在后台线程中初始化数据，避免阻塞
    init_thread = threading.Thread(target=_init_data_thread, daemon=False)
    init_thread.start()
    
    # 等待数据初始化完成（使用异步等待，增加超时检查）
    max_wait_time = 300  # 最多等待5分钟
    wait_interval = 0.5  # 每0.5秒检查一次
    waited_time = 0
    
    while not _data_ready.is_set():
        await asyncio.sleep(wait_interval)
        waited_time += wait_interval
        if waited_time >= max_wait_time:
            raise RuntimeError(f"数据初始化超时（{max_wait_time}秒）")
        if waited_time % 5 == 0:  # 每5秒输出一次等待信息
            print(f"等待数据初始化中... (已等待 {waited_time:.1f}秒)")
    
    # 获取初始化完成的数据
    data_df = _data_df
    
    # 确保数据已完全加载
    if data_df is None or data_df.empty:
        raise RuntimeError("数据初始化失败：DataFrame为空")
    
    print("=" * 60)
    print("开始创建DataTable实例...")
    print("=" * 60)
    
    # 根据DataFrame生成列配置
    columns_config = generate_columns_config_from_dataframe(data_df)
    # 创建DataTable实例
    data_table = DataTable(dataframe=data_df, columns_config=columns_config)
    
    # 设置全局DataTable实例
    set_data_table(data_table)
    set_data_initialized(True)
    
    print("=" * 60)
    print(f"DataTable实例创建完成！")
    print(f"  - 列数: {len(columns_config)}")
    print(f"  - 数据行数: {len(data_df)}")
    print(f"  - 状态: 已就绪，可以处理请求")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
