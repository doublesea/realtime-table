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
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
    """初始化数据，生成指定数量的数据并保存到DataFrame（优化版本）
    测试完全不同的字段组合，验证前端动态字段显示功能
    """
    logger.info(f"开始生成 {TOTAL_RECORDS} 条数据...")
    start_time = datetime.now()
    
    # 全新的字段定义 - 订单/交易数据
    order_statuses = ['待付款', '已付款', '已发货', '已完成', '已取消', '退款中']
    payment_methods = ['支付宝', '微信支付', '银行卡', '现金', 'PayPal']
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆']
    merchants = ['商家A', '商家B', '商家C', '商家D', '商家E', '商家F', '商家G']
    
    # 使用向量化操作高效生成数据
    ids = np.arange(1, TOTAL_RECORDS + 1, dtype=np.int64)
    
    # 使用numpy的随机数生成（基于ID作为种子，确保可重复）
    np.random.seed(42)  # 固定种子，保证整体可重复
    
    # 生成订单号
    order_numbers = [f"ORD{str(id).zfill(10)}" for id in ids]
    
    # 生成订单状态（使用ID作为索引确保可重复）
    status_indices = (ids - 1) % len(order_statuses)
    status_values = np.array(order_statuses)[status_indices]
    
    # 生成支付方式（使用ID作为索引确保可重复）
    payment_indices = (ids * 3) % len(payment_methods)
    payment_values = np.array(payment_methods)[payment_indices]
    
    # 生成订单金额（10-10000，保留两位小数）
    order_amounts = np.round(np.random.uniform(10, 10000, size=TOTAL_RECORDS), 2)
    
    # 生成商品数量（1-100）
    item_counts = np.random.randint(1, 101, size=TOTAL_RECORDS)
    
    # 生成配送费用（0-50，保留一位小数）
    shipping_costs = np.round(np.random.uniform(0, 50, size=TOTAL_RECORDS), 1)
    
    # 生成城市（使用ID作为索引确保可重复）
    city_indices = (ids * 7) % len(cities)
    city_values = np.array(cities)[city_indices]
    
    # 生成商家（使用ID作为索引确保可重复）
    merchant_indices = (ids * 11) % len(merchants)
    merchant_values = np.array(merchants)[merchant_indices]
    
    # 生成用户ID（1000-99999）
    user_ids = np.random.randint(1000, 100000, size=TOTAL_RECORDS)
    
    # 生成折扣率（0-0.5，保留两位小数）
    discounts = np.round(np.random.uniform(0, 0.5, size=TOTAL_RECORDS), 2)
    
    # 生成日期偏移（0-730天，即2年内）
    day_offsets = np.random.randint(0, 731, size=TOTAL_RECORDS)
    base_date = datetime.now()
    # 使用列表推导式生成日期字符串
    order_dates = [(base_date - timedelta(days=int(offset))).strftime('%Y-%m-%d') for offset in day_offsets]
    
    # 生成ts列（时间戳，float类型，微秒精度）- 生成过去2年内的随机时间戳
    # 时间戳范围：当前时间往前2年到当前时间
    base_timestamp = base_date.timestamp()
    two_years_seconds = 2 * 365 * 24 * 3600
    # 生成随机秒数偏移（0到2年），包含微秒精度
    seconds_offsets = np.random.uniform(0, two_years_seconds, size=TOTAL_RECORDS)
    # 生成时间戳（float类型，包含秒和微秒）
    timestamps = base_timestamp - seconds_offsets
    
    # 生成16进制码流字段（订单备注）- 每个字节之间有空格，长度50左右
    # 使用ID作为随机种子，确保相同ID生成相同的数据
    byte_count = 50
    hex_streams = []
    
    # 生成payload字段（bytes类型）- 真正的bytes对象，长度100左右
    payload_byte_count = 16
    payload_bytes_list = []
    
    # 保存当前随机状态
    original_state = np.random.get_state()
    
    for id_val in ids:
        # 将numpy类型转换为Python int，避免类型错误
        seed = int(id_val)
        # 创建独立的随机数生成器，使用ID作为种子
        rng = np.random.RandomState(seed)
        # 生成50个字节的随机数据（0-255）
        random_bytes = rng.randint(0, 256, size=byte_count, dtype=np.uint8)
        # 转换为16进制字符串，每个字节之间加空格，使用大写字母
        hex_string = ' '.join([f'{int(b):02X}' for b in random_bytes])
        hex_streams.append(hex_string)
        
        # 生成payload字段的随机数据（使用不同的种子确保与order_remark不同）
        payload_rng = np.random.RandomState(seed + 10000)
        payload_bytes_array = payload_rng.randint(0, 256, size=payload_byte_count, dtype=np.uint8)
        # 转换为Python bytes对象
        payload_bytes = bytes(payload_bytes_array.tolist())
        payload_bytes_list.append(payload_bytes)
    
    # 恢复原始随机状态
    np.random.set_state(original_state)
    
    # 创建DataFrame（使用字典方式，更高效）
    data_df = pd.DataFrame({
        'id': ids,
        'order_number': order_numbers,
        'order_status': status_values,
        'payment_method': payment_values,
        'order_amount': order_amounts,
        'item_count': item_counts,
        'shipping_cost': shipping_costs,
        'city': city_values,
        'merchant': merchant_values,
        'user_id': user_ids,
        'discount': discounts,
        'order_date': order_dates,
        # 'order_remark': hex_streams,  # 16进制码流字段
        'payload': payload_bytes_list,  # payload字段（真正的bytes类型）
        'ts': timestamps  # 时间戳字段（float类型）
    })
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"数据生成完成，共 {len(data_df)} 条记录，总耗时: {elapsed:.2f}秒")
    logger.debug(f"字段列表: {list(data_df.columns)}")
    
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
        logger.info("数据已在外部初始化，跳过startup_event中的初始化")
        return
    
    logger.info("开始初始化数据...")
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
            logger.error(f"数据初始化超时（{max_wait_time}秒）")
            raise RuntimeError(f"数据初始化超时（{max_wait_time}秒）")
    
    # 获取初始化完成的数据
    data_df = _data_df
    
    # 确保数据已完全加载
    if data_df is None or data_df.empty:
        logger.error("数据初始化失败：DataFrame为空")
        raise RuntimeError("数据初始化失败：DataFrame为空")
    
    logger.info("开始创建DataTable实例...")
    # 根据DataFrame生成列配置
    columns_config = generate_columns_config_from_dataframe(data_df)
    # 创建DataTable实例
    data_table = DataTable(dataframe=data_df, columns_config=columns_config)
    
    # 设置全局DataTable实例
    set_data_table(data_table)
    set_data_initialized(True)
    logger.info(f"DataTable实例创建完成！列数: {len(columns_config)}, 数据行数: {len(data_df)}")


if __name__ == "__main__":
    import uvicorn
    import socket
    
    # 检查端口是否可用
    def check_port(port: int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return True
    
    if not check_port(3001):
        logger.error("端口 3001 已被占用，请先终止占用端口的进程，或使用其他端口")
        exit(1)
    
    logger.info("启动 FastAPI 服务（端口: 3001）")
    logger.info("建议使用 nicegui_vue_embed.py 启动完整应用")
    uvicorn.run(app, host="0.0.0.0", port=3001)
