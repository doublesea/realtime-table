"""API路由 - 负责与前端通信

包含FastAPI应用实例、数据模型和所有API路由端点。
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Union, Any
import asyncio
import logging

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
class NumberFilter(BaseModel):
    operator: Optional[str] = None  # '=', '>', '<', '>=', '<='
    value: Optional[Union[int, float, str]] = None  # 支持整数、浮点数和字符串（支持16进制如0x123）


class FilterGroup(BaseModel):
    filters: List[NumberFilter]
    logic: Optional[str] = 'AND'  # 'AND' 或 'OR'


class FilterParams(BaseModel):
    """动态筛选参数，支持任意字段名"""
    model_config = {"extra": "allow"}  # 允许额外字段
    
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

