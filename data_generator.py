"""数据生成器 - 本地函数实现，不依赖API"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np


def generate_single_record(start_id: Optional[int] = None) -> dict:
    """生成单条随机数据记录
    
    Args:
        start_id: 起始ID（用于生成唯一ID），如果为None则使用当前时间戳
    
    Returns:
        单条数据记录的字典
    """
    # 字段定义
    order_statuses = ['待付款', '已付款', '已发货', '已完成', '已取消', '退款中']
    payment_methods = ['支付宝', '微信支付', '银行卡', '现金', 'PayPal']
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆']
    merchants = ['商家A', '商家B', '商家C', '商家D', '商家E', '商家F', '商家G']
    
    # 生成唯一ID（如果没有提供，使用时间戳）
    if start_id is None:
        record_id = int(datetime.now().timestamp() * 1000000) % 1000000000
    else:
        record_id = start_id
    
    # 生成订单号
    order_number = f"ORD{str(record_id).zfill(10)}"
    
    # 生成随机数据
    order_status = random.choice(order_statuses)
    payment_method = random.choice(payment_methods)
    order_amount = round(random.uniform(10, 10000), 2)
    item_count = random.randint(1, 100)
    shipping_cost = round(random.uniform(0, 50), 1)
    city = random.choice(cities)
    merchant = random.choice(merchants)
    user_id = random.randint(1000, 99999)
    discount = round(random.uniform(0, 0.5), 2)
    
    # 生成日期（过去2年内）
    day_offset = random.randint(0, 730)
    order_date = (datetime.now() - timedelta(days=day_offset)).strftime('%Y-%m-%d')
    
    # 生成时间戳（过去2年内，包含微秒精度）
    base_timestamp = datetime.now().timestamp()
    seconds_offset = random.uniform(0, 2 * 365 * 24 * 3600)
    ts = base_timestamp - seconds_offset
    
    # 生成payload字段（bytes类型）
    payload_byte_count = 16
    payload_bytes = bytes([random.randint(0, 255) for _ in range(payload_byte_count)])
    
    return {
        'id': record_id,
        'order_number': order_number,
        'order_status': order_status,
        'payment_method': payment_method,
        'order_amount': order_amount,
        'item_count': item_count,
        'shipping_cost': shipping_cost,
        'city': city,
        'merchant': merchant,
        'user_id': user_id,
        'discount': discount,
        'order_date': order_date,
        'payload': payload_bytes,
        'ts': ts
    }


def generate_batch_records(start_id: int, count: int) -> List[Dict]:
    """批量生成随机数据记录
    
    Args:
        start_id: 起始ID
        count: 生成数量
    
    Returns:
        数据记录列表
    """
    if count <= 0:
        return []

    # 字段定义
    order_statuses = ['待付款', '已付款', '已发货', '已完成', '已取消', '退款中']
    payment_methods = ['支付宝', '微信支付', '银行卡', '现金', 'PayPal']
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安', '南京', '重庆']
    merchants = ['商家A', '商家B', '商家C', '商家D', '商家E', '商家F', '商家G']
    
    # 预生成基础数据
    ids = np.arange(start_id, start_id + count)
    
    # 生成订单号
    order_numbers = [f"ORD{str(rid).zfill(10)}" for rid in ids]
    
    # 随机选择分类字段
    batch_statuses = np.random.choice(order_statuses, count)
    batch_payments = np.random.choice(payment_methods, count)
    batch_cities = np.random.choice(cities, count)
    batch_merchants = np.random.choice(merchants, count)
    
    # 生成数值字段
    batch_amounts = np.round(np.random.uniform(10, 10000, count), 2)
    batch_item_counts = np.random.randint(1, 101, count)
    batch_shipping_costs = np.round(np.random.uniform(0, 50, count), 1)
    batch_user_ids = np.random.randint(1000, 100000, count)
    batch_discounts = np.round(np.random.uniform(0, 0.5, count), 2)
    
    # 生成日期
    base_date = datetime.now()
    days_offsets = np.random.randint(0, 731, count)
    batch_dates = [(base_date - timedelta(days=int(d))).strftime('%Y-%m-%d') for d in days_offsets]
    
    # 生成时间戳
    base_timestamp = base_date.timestamp()
    seconds_offsets = np.random.uniform(0, 2 * 365 * 24 * 3600, count)
    batch_ts = base_timestamp - seconds_offsets
    
    # 生成Payload (bytes)
    batch_payloads = [bytes(np.random.randint(0, 256, 16, dtype=np.uint8)) for _ in range(count)]
    
    # 组装数据
    records = []
    for i in range(count):
        records.append({
            'id': int(ids[i]),
            'order_number': order_numbers[i],
            'order_status': str(batch_statuses[i]),
            'payment_method': str(batch_payments[i]),
            'order_amount': float(batch_amounts[i]),
            'item_count': int(batch_item_counts[i]),
            'shipping_cost': float(batch_shipping_costs[i]),
            'city': str(batch_cities[i]),
            'merchant': str(batch_merchants[i]),
            'user_id': int(batch_user_ids[i]),
            'discount': float(batch_discounts[i]),
            'order_date': batch_dates[i],
            'payload': batch_payloads[i],
            'ts': float(batch_ts[i])
        })
        
    return records

