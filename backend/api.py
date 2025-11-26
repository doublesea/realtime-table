"""API路由 - 负责与前端通信

包含FastAPI应用实例、数据模型和所有API路由端点。
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List, Union, Dict, Any
from datetime import datetime
import asyncio
import logging
import json

# 配置日志
logger = logging.getLogger(__name__)

# 导入DataTable类
try:
    from .data_table import DataTable, ColumnConfig
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    from backend.data_table import DataTable, ColumnConfig

# 全局DataTable实例
data_table: Optional[DataTable] = None
# 数据初始化状态标志
_data_initialized = False
# 自动添加数据任务
_auto_add_task: Optional[asyncio.Task] = None
_auto_add_running = False


# FastAPI应用实例
app = FastAPI(title="大数据量表格API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，包括 NiceGUI 页面
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class TableData(BaseModel):
    id: int
    name: str
    email: str
    age: int
    department: str
    salary: int
    status: str
    createTime: str


class NumberFilter(BaseModel):
    operator: Optional[str] = None  # '=', '>', '<', '>=', '<='
    value: Optional[Union[int, float, str]] = None  # 支持整数、浮点数和字符串（支持16进制如0x123）


class FilterGroup(BaseModel):
    filters: List[NumberFilter]
    logic: Optional[str] = 'AND'  # 'AND' 或 'OR'


class FilterParams(BaseModel):
    """动态筛选参数，支持任意字段名"""
    model_config = {"extra": "allow"}  # 允许额外字段
    
    # 保留向后兼容的字段（可选）
    id: Optional[Union[NumberFilter, FilterGroup]] = None
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[Union[str, List[str]]] = None
    status: Optional[Union[str, List[str]]] = None
    age: Optional[Union[NumberFilter, FilterGroup]] = None
    salary: Optional[Union[NumberFilter, FilterGroup]] = None
    createTime: Optional[str] = None
    
    @classmethod
    def parse_dynamic_filter(cls, field_name: str, value: Any) -> Any:
        """动态解析筛选值，根据值的类型判断是 NumberFilter、FilterGroup 还是普通值"""
        if value is None:
            return None
        if isinstance(value, dict):
            # 如果有 filters 键，说明是 FilterGroup
            if 'filters' in value:
                return FilterGroup(**value)
            # 如果有 operator 或 value，说明是 NumberFilter
            elif 'operator' in value or 'value' in value:
                return NumberFilter(**value)
        # 其他情况直接返回
        return value


class ListRequest(BaseModel):
    page: int = 1
    pageSize: int = 100
    filters: Optional[FilterParams] = None
    sortBy: Optional[str] = None  # 排序字段
    sortOrder: Optional[str] = None  # 排序方向: 'ascending' 或 'descending'


class ListResponse(BaseModel):
    list: List[TableData]
    total: int
    page: int
    pageSize: int


def set_data_table(table: DataTable):
    """设置全局DataTable实例"""
    global data_table
    data_table = table


def set_data_initialized(initialized: bool):
    """设置数据初始化状态"""
    global _data_initialized
    _data_initialized = initialized


def get_data_table() -> Optional[DataTable]:
    """获取全局DataTable实例"""
    return data_table


def is_data_initialized() -> bool:
    """检查数据是否已初始化"""
    return _data_initialized


# API路由
@app.get("/")
async def root():
    return {"message": "大数据量表格API服务运行中"}


@app.post("/api/data/list")
async def get_data_list(request: ListRequest):
    """获取数据列表（支持分页和筛选）"""
    try:
        # 如果数据未初始化，等待一小段时间后重试
        if data_table is None or not _data_initialized:
            # 等待最多30秒
            max_wait = 60  # 60次 * 0.5秒 = 30秒
            for i in range(max_wait):
                await asyncio.sleep(0.5)
                if data_table is not None and _data_initialized:
                    break
            if data_table is None or not _data_initialized:
                raise HTTPException(
                    status_code=503, 
                    detail=f"数据正在初始化中，请稍后重试。当前状态: data_table={'已创建' if data_table else '未创建'}, _data_initialized={_data_initialized}"
                )
        
        # 使用DataTable类获取数据
        result_data = data_table.get_list(
            filters=request.filters,
            page=request.page,
            page_size=request.pageSize,
            sort_by=request.sortBy,
            sort_order=request.sortOrder
        )
        
        result = {
            "success": True,
            "data": result_data
        }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/row-position")
async def get_row_position(request: dict):
    """获取选中行在筛选结果中的位置"""
    try:
        # 如果数据未初始化，等待一小段时间后重试
        if data_table is None or not _data_initialized:
            max_wait = 60
            for i in range(max_wait):
                await asyncio.sleep(0.5)
                if data_table is not None and _data_initialized:
                    break
            if data_table is None or not _data_initialized:
                raise HTTPException(status_code=503, detail="数据正在初始化中，请稍后重试")
        
        row_id = request.get('rowId')
        filters = request.get('filters')
        
        if row_id is None:
            raise HTTPException(status_code=400, detail="缺少rowId参数")
        
        # 构建筛选条件
        filter_params = None
        if filters:
            try:
                filter_params = FilterParams(**filters)
            except Exception as e:
                logger.warning(f"行位置查询 - 筛选条件解析失败: {e}, filters: {filters}")
                # 即使解析失败，也尝试使用空筛选条件继续查询
                pass
        
        # 使用DataTable类获取行位置
        position_data = data_table.get_row_position(row_id, filter_params)
        
        return {
            "success": True,
            "data": position_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行位置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/row-detail")
async def get_row_detail(request: dict):
    """获取行的详细信息
    接收行数据，生成并返回需要展示的详细信息
    """
    try:
        # 如果数据未初始化，等待一小段时间后重试
        if data_table is None or not _data_initialized:
            max_wait = 60
            for i in range(max_wait):
                await asyncio.sleep(0.5)
                if data_table is not None and _data_initialized:
                    break
            if data_table is None or not _data_initialized:
                raise HTTPException(status_code=503, detail="数据正在初始化中，请稍后重试")
        
        # 获取行数据
        row_data = request.get('row')
        if not row_data:
            raise HTTPException(status_code=400, detail="缺少row参数")
        
        # 从行数据中提取ID
        row_id = row_data.get('id')
        if row_id is None:
            raise HTTPException(status_code=400, detail="行数据中缺少id字段")
        
        # 使用DataTable类获取行详情
        try:
            detail = data_table.get_row_detail(row_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        
        return {
            "success": True,
            "data": detail
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/columns")
async def get_columns_config():
    """获取列配置信息"""
    try:
        # 如果数据未初始化，等待一小段时间后重试
        if data_table is None or not _data_initialized:
            # 等待最多30秒
            max_wait = 60
            for i in range(max_wait):
                await asyncio.sleep(0.5)
                if data_table is not None and _data_initialized:
                    break
            if data_table is None or not _data_initialized:
                raise HTTPException(status_code=503, detail="数据正在初始化中，请稍后重试")
        
        # 使用DataTable类获取列配置
        columns_data = data_table.get_columns_config()
        
        return {
            "success": True,
            "data": columns_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取列配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/filters")
async def get_filters():
    """获取筛选选项（从当前数据中动态提取）"""
    try:
        if data_table is None or not _data_initialized:
            raise HTTPException(status_code=503, detail="数据未初始化")
        
        # 从列配置中提取筛选选项
        filter_options = {}
        for col_config in data_table.columns_config:
            if col_config.filterType in ['multi-select', 'select'] and col_config.options:
                filter_options[col_config.prop] = col_config.options
        
        return {
            "success": True,
            "data": filter_options
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取筛选选项失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/add")
async def add_data(request: dict):
    """动态添加新数据到表格
    
    请求参数:
        data: 新数据，可以是单个字典或字典列表
    """
    try:
        # 如果数据未初始化，等待一小段时间后重试
        if data_table is None or not _data_initialized:
            max_wait = 60
            for i in range(max_wait):
                await asyncio.sleep(0.5)
                if data_table is not None and _data_initialized:
                    break
            if data_table is None or not _data_initialized:
                raise HTTPException(status_code=503, detail="数据正在初始化中，请稍后重试")
        
        # 获取新数据
        new_data = request.get('data')
        if not new_data:
            raise HTTPException(status_code=400, detail="缺少data参数")
        
        # 调用DataTable的add_data方法
        result = data_table.add_data(new_data)
        
        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加数据失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def generate_single_record(start_id: int = None) -> dict:
    """生成单条随机数据记录
    
    Args:
        start_id: 起始ID（用于生成唯一ID），如果为None则使用当前时间戳
    
    Returns:
        单条数据记录的字典
    """
    import random
    from datetime import datetime, timedelta
    import numpy as np
    
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


async def auto_add_data_task(batch_size: int = 1, interval: float = 0.5):
    """自动添加数据的后台任务
    
    Args:
        batch_size: 每批添加的数据条数
        interval: 添加间隔（秒）
    """
    global _auto_add_running, data_table
    current_id = int(datetime.now().timestamp() * 1000000) % 1000000000
    
    while _auto_add_running:
        try:
            if data_table is None or not _data_initialized:
                await asyncio.sleep(interval)
                continue
            
            # 生成一批数据
            batch_data = []
            for i in range(batch_size):
                record = generate_single_record(current_id + i)
                batch_data.append(record)
            current_id += batch_size
            
            # 添加到表格
            result = data_table.add_data(batch_data)
            logger.info(f"自动添加数据: {result['added_count']} 条")
            
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"自动添加数据失败: {str(e)}", exc_info=True)
            await asyncio.sleep(interval)


@app.post("/api/data/auto-add/start")
async def start_auto_add(request: Request):
    """启动自动添加数据任务
    
    请求参数（可选）:
        batch_size: 每批添加的数据条数（默认1）
        interval: 添加间隔，单位秒（默认0.5）
    """
    global _auto_add_task, _auto_add_running
    
    if _auto_add_running:
        return {
            "success": False,
            "message": "自动添加任务已在运行中"
        }
    
    batch_size = 1
    interval = 0.5
    
    # 从请求体中获取参数
    try:
        body = await request.json()
        if body:
            batch_size = body.get('batch_size', 1)
            interval = body.get('interval', 0.5)
    except:
        # 如果解析失败，使用默认值
        pass
    
    _auto_add_running = True
    _auto_add_task = asyncio.create_task(auto_add_data_task(batch_size, interval))
    
    logger.info(f"启动自动添加数据任务: batch_size={batch_size}, interval={interval}秒")
    
    return {
        "success": True,
        "message": f"自动添加任务已启动（每{interval}秒添加{batch_size}条数据）"
    }


@app.post("/api/data/auto-add/stop")
async def stop_auto_add():
    """停止自动添加数据任务"""
    global _auto_add_task, _auto_add_running
    
    if not _auto_add_running:
        return {
            "success": False,
            "message": "自动添加任务未在运行"
        }
    
    _auto_add_running = False
    if _auto_add_task:
        _auto_add_task.cancel()
        try:
            await _auto_add_task
        except asyncio.CancelledError:
            pass
        _auto_add_task = None
    
    logger.info("停止自动添加数据任务")
    
    return {
        "success": True,
        "message": "自动添加任务已停止"
    }


@app.get("/api/data/auto-add/status")
async def get_auto_add_status():
    """获取自动添加数据任务状态"""
    return {
        "success": True,
        "data": {
            "running": _auto_add_running
        }
    }
