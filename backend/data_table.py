"""DataTable类 - 表格数据管理类

封装表格的数据处理功能，包括筛选、分页、排序等操作。
初始化时传入DataFrame格式的数据和列配置。
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import pandas as pd
import re


class ColumnConfig(BaseModel):
    """列配置模型"""
    prop: str  # 字段名
    label: str  # 列标题
    type: str  # 数据类型: 'string', 'number', 'date', 'boolean', 'bytes'
    sortable: Optional[bool] = True  # 是否可排序
    filterable: Optional[bool] = True  # 是否可筛选
    filterType: Optional[str] = 'text'  # 筛选类型: 'text', 'number', 'select', 'multi-select', 'date', 'none'
    minWidth: Optional[int] = 120  # 最小宽度
    width: Optional[int] = None  # 固定宽度
    fixed: Optional[bool | str] = False  # 是否固定: 'left', 'right', False
    options: Optional[List[str]] = None  # 下拉选项（用于select类型）


# 使用TYPE_CHECKING避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    try:
        from .api import FilterParams, FilterGroup
    except ImportError:
        from backend.api import FilterParams, FilterGroup


class DataTable:
    """表格数据管理类
    
    封装表格的数据处理功能，包括筛选、分页、排序等操作。
    初始化时传入DataFrame格式的数据和列配置。
    """
    
    def __init__(self, dataframe: pd.DataFrame, columns_config: List[ColumnConfig]):
        """
        初始化表格类
        
        Args:
            dataframe: pandas DataFrame格式的数据（可以为空，但必须有正确的列结构）
            columns_config: 列配置列表，定义每列的属性（字段名、类型、筛选方式等）
        """
        import threading
        self._lock = threading.RLock()
        
        if dataframe is None:
            raise ValueError("DataFrame不能为None")
        if not columns_config:
            raise ValueError("列配置不能为空")
        
        # 如果 DataFrame 为空，确保它有正确的列结构
        if dataframe.empty:
            # 从列配置中获取列名
            expected_columns = [col.prop for col in columns_config]
            # 创建具有正确列结构的空 DataFrame
            self.dataframe = pd.DataFrame(columns=expected_columns)
        else:
            self.dataframe = dataframe.copy()
        
        self.columns_config = columns_config
        # 验证列配置中的字段是否存在于DataFrame中
        self._validate_columns()
    
    @property
    def total_count(self) -> int:
        """获取总数据量"""
        return len(self.dataframe)
    
    def _validate_columns(self):
        """验证列配置中的字段是否存在于DataFrame中"""
        df_columns = set(self.dataframe.columns)
        config_props = {col.prop for col in self.columns_config}
        
        missing_in_df = config_props - df_columns
        if missing_in_df:
            raise ValueError(f"列配置中定义的字段在DataFrame中不存在: {missing_in_df}")
    
    def _parse_number_value(self, value: Any) -> Union[int, float, None]:
        """解析数字值，支持16进制字符串（如0x123）"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            # 尝试解析16进制字符串
            value_stripped = value.strip()
            if value_stripped.startswith('0x') or value_stripped.startswith('0X'):
                try:
                    return int(value_stripped, 16)
                except ValueError:
                    # 如果解析失败，尝试作为普通数字
                    try:
                        return float(value_stripped) if '.' in value_stripped else int(value_stripped)
                    except ValueError:
                        return None
            else:
                # 尝试作为普通数字解析
                try:
                    return float(value_stripped) if '.' in value_stripped else int(value_stripped)
                except ValueError:
                    return None
        return None
    
    def _build_pandas_filter(self, filters: Optional['FilterParams'] = None, df: Optional[pd.DataFrame] = None) -> pd.Series:
        """将筛选条件转换为pandas布尔索引（动态处理任意字段）"""
        # 延迟导入避免循环依赖
        try:
            from .api import FilterParams, FilterGroup, NumberFilter  # type: ignore
        except ImportError:
            from backend.api import FilterParams, FilterGroup, NumberFilter  # type: ignore
        
        # 使用传入的df或self.dataframe
        target_df = df if df is not None else self.dataframe
        
        # 如果 DataFrame 为空，返回空掩码
        if target_df.empty:
            return pd.Series([], dtype=bool)
        
        if not filters:
            # 使用 index 创建掩码，确保索引一致
            return pd.Series([True] * len(target_df), index=target_df.index)
        
        # 初始化筛选掩码，使用 DataFrame 的索引
        mask = pd.Series([True] * len(target_df), index=target_df.index)
        
        # 获取筛选参数字典
        filter_dict = filters.model_dump(exclude_none=True) if hasattr(filters, 'model_dump') else filters.dict(exclude_none=True) if hasattr(filters, 'dict') else {}
        
        # 遍历所有筛选字段（包括动态字段和旧字段）
        for field_name, filter_value in filter_dict.items():
            
            # 检查字段是否存在于DataFrame中
            if field_name not in target_df.columns:
                continue
            
            # 查找对应的列配置
            col_config = next((c for c in self.columns_config if c.prop == field_name), None)
            if not col_config or not col_config.filterable:
                continue
            
            # 根据筛选类型处理
            if col_config.filterType == 'number':
                # 数字类型筛选
                # 处理 FilterGroup 或 NumberFilter 实例
                if isinstance(filter_value, FilterGroup):
                    filters_mask = []
                    for num_filter in filter_value.filters:
                        if num_filter.operator and num_filter.value is not None:
                            op = num_filter.operator
                            val = self._parse_number_value(num_filter.value)
                            if val is None:
                                continue
                            if op == '=':
                                filters_mask.append(target_df[field_name] == val)
                            elif op == '>':
                                filters_mask.append(target_df[field_name] > val)
                            elif op == '<':
                                filters_mask.append(target_df[field_name] < val)
                            elif op == '>=':
                                filters_mask.append(target_df[field_name] >= val)
                            elif op == '<=':
                                filters_mask.append(target_df[field_name] <= val)
                    
                    if filters_mask:
                        logic = filter_value.logic or 'AND'
                        if logic.upper() == 'OR':
                            field_mask = filters_mask[0]
                            for m in filters_mask[1:]:
                                field_mask |= m
                        else:
                            field_mask = filters_mask[0]
                            for m in filters_mask[1:]:
                                field_mask &= m
                        mask &= field_mask
                elif isinstance(filter_value, NumberFilter):
                    if filter_value.operator and filter_value.value is not None:
                        op = filter_value.operator
                        val = self._parse_number_value(filter_value.value)
                        if val is not None:
                            if op == '=':
                                mask &= (target_df[field_name] == val)
                            elif op == '>':
                                mask &= (target_df[field_name] > val)
                            elif op == '<':
                                mask &= (target_df[field_name] < val)
                            elif op == '>=':
                                mask &= (target_df[field_name] >= val)
                            elif op == '<=':
                                mask &= (target_df[field_name] <= val)
                # 处理字典格式（从 JSON 解析来的）
                elif isinstance(filter_value, dict):
                    if 'filters' in filter_value:
                        # FilterGroup（多条件）
                        filter_group = FilterGroup(**filter_value)
                        filters_mask = []
                        for num_filter in filter_group.filters:
                            if num_filter.operator and num_filter.value is not None:
                                op = num_filter.operator
                                val = self._parse_number_value(num_filter.value)
                                if val is None:
                                    continue
                                if op == '=':
                                    filters_mask.append(target_df[field_name] == val)
                                elif op == '>':
                                    filters_mask.append(target_df[field_name] > val)
                                elif op == '<':
                                    filters_mask.append(target_df[field_name] < val)
                                elif op == '>=':
                                    filters_mask.append(target_df[field_name] >= val)
                                elif op == '<=':
                                    filters_mask.append(target_df[field_name] <= val)
                        
                        if filters_mask:
                            logic = filter_group.logic or 'AND'
                            if logic.upper() == 'OR':
                                field_mask = filters_mask[0]
                                for m in filters_mask[1:]:
                                    field_mask |= m
                            else:
                                field_mask = filters_mask[0]
                                for m in filters_mask[1:]:
                                    field_mask &= m
                            mask &= field_mask
                    elif 'operator' in filter_value or 'value' in filter_value:
                        # NumberFilter（单条件）
                        num_filter = NumberFilter(**filter_value)
                        if num_filter.operator and num_filter.value is not None:
                            op = num_filter.operator
                            val = self._parse_number_value(num_filter.value)
                            if val is not None:
                                if op == '=':
                                    mask &= (target_df[field_name] == val)
                                elif op == '>':
                                    mask &= (target_df[field_name] > val)
                                elif op == '<':
                                    mask &= (target_df[field_name] < val)
                                elif op == '>=':
                                    mask &= (target_df[field_name] >= val)
                                elif op == '<=':
                                    mask &= (target_df[field_name] <= val)
            
            elif col_config.filterType == 'text':
                # 文本筛选
                if isinstance(filter_value, str) and filter_value:
                    # 对于bytes类型字段，需要先转换为16进制字符串再筛选
                    if col_config.type == 'bytes':
                        # 优化：使用向量化操作而不是apply（性能提升）
                        try:
                            # 尝试直接使用字符串操作（如果已经是字符串类型）
                            if target_df[field_name].dtype == 'object':
                                # 检查第一个非空值是否为bytes
                                sample = target_df[field_name].dropna()
                                if len(sample) > 0 and isinstance(sample.iloc[0], bytes):
                                    # 使用向量化操作：批量转换bytes为hex字符串
                                    # 注意：pandas的apply在大量数据时很慢，但bytes转换无法完全向量化
                                    # 我们使用更高效的方式：只对非空值进行转换
                                    hex_series = target_df[field_name].apply(
                                        lambda val: ' '.join([f'{b:02X}' for b in val]) if isinstance(val, bytes) else str(val)
                                    )
                                    mask &= hex_series.str.contains(filter_value, case=False, na=False)
                                else:
                                    # 已经是字符串，直接筛选
                                    mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                            else:
                                # 直接转换为字符串筛选
                                mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                        except Exception:
                            # 如果转换失败，回退到原始方法
                            mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                    else:
                        # 普通文本字段：直接使用字符串操作（已优化）
                        mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
            
            elif col_config.filterType == 'date':
                # 日期筛选
                if isinstance(filter_value, str) and filter_value:
                    # 如果是ts字段（时间戳），需要特殊处理
                    if field_name == 'ts':
                        from datetime import datetime
                        # 优化：使用向量化操作（虽然apply仍然需要，但尽量减少计算）
                        try:
                            # 将时间戳转换为字符串进行文本匹配（支持部分匹配，如只输入时间）
                            def timestamp_to_str(ts):
                                """将时间戳转换为字符串用于匹配"""
                                try:
                                    dt = datetime.fromtimestamp(float(ts))
                                    microseconds = int((float(ts) % 1) * 1000000)
                                    return dt.strftime('%Y-%m-%d %H:%M:%S') + f'.{microseconds:06d}'
                                except (ValueError, OSError):
                                    return str(ts)
                            
                            # 将ts列转换为字符串进行文本匹配（支持部分匹配）
                            # 注意：对于大量数据，这仍然可能较慢，但提供了灵活性
                            ts_str_series = target_df[field_name].apply(timestamp_to_str)
                            mask &= ts_str_series.str.contains(filter_value, case=False, na=False)
                        except Exception:
                            # 如果转换失败，尝试直接字符串匹配
                            mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                    else:
                        # 普通日期字段，直接字符串匹配
                        mask &= (target_df[field_name].astype(str) == filter_value)
            
            elif col_config.filterType in ['multi-select', 'select']:
                # 多选或单选筛选
                # 统一处理：如果是单个值，转换为列表
                if isinstance(filter_value, list):
                    filter_list = filter_value
                elif filter_value is not None and filter_value != '':
                    filter_list = [filter_value]
                else:
                    continue
                
                if len(filter_list) > 0:
                    # 确保 DataFrame 列的数据类型匹配
                    try:
                        mask &= target_df[field_name].isin(filter_list)
                    except Exception as e:
                        # 尝试转换为字符串后再筛选
                        try:
                            mask &= target_df[field_name].astype(str).isin([str(v) for v in filter_list])
                        except Exception as e2:
                            pass
        
        return mask
    
    def get_list(self, 
                 filters: Optional['FilterParams'] = None,
                 page: int = 1,
                 page_size: int = 100,
                 sort_by: Optional[str] = None,
                 sort_order: Optional[str] = None) -> Dict[str, Any]:
        """获取数据列表（支持筛选、分页、排序）
        
        Args:
            filters: 筛选条件
            page: 页码
            page_size: 每页大小
            sort_by: 排序字段
            sort_order: 排序方向 ('ascending' 或 'descending')
        
        Returns:
            包含list、total、page、pageSize的字典
        """
        # 使用锁保护读取，并创建dataframe快照以确保操作的一致性
        with self._lock:
            current_df = self.dataframe
            # 如果 dataframe 是 None (虽然初始化检查过，但为了安全)
            if current_df is None:
                import logging
                logger = logging.getLogger(__name__)
                logger.error("DataFrame 未初始化 or None")
                return {
                    "list": [],
                    "total": 0,
                    "page": page,
                    "pageSize": page_size
                }
        
        # 以下操作使用 current_df 快照，无需持有锁（除非涉及到其他共享状态）
        # 注意：current_df 是一个引用，如果 add_data 替换了 self.dataframe，current_df 指向旧对象，这是安全的。
        
        if current_df.empty:
            return {
                "list": [],
                "total": 0,
                "page": page,
                "pageSize": page_size
            }
        
        # 验证 DataFrame 的完整性（防止数据被意外清空）
        dataframe_length = len(current_df)
        
        # 记录当前长度（用于下次验证）- 注意：写入 _last_known_length 也应该是线程安全的，但这里只是用于日志，暂不加锁
        if not hasattr(self, '_last_known_length'):
            self._last_known_length = dataframe_length
        
        if dataframe_length == 0 and self._last_known_length > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.critical(
                f"🚨 检测到 DataFrame 被意外清空！上次已知长度: {self._last_known_length}, "
                f"当前长度: {dataframe_length}. 这会导致表格显示为空！"
            )
        elif dataframe_length < self._last_known_length and self._last_known_length > 100:
            # 如果数据量突然减少很多，也记录警告
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"⚠️ 数据量异常减少: 从 {self._last_known_length} 减少到 {dataframe_length}, "
                f"减少了 {self._last_known_length - dataframe_length} 行"
            )
        
        # 更新记录的长度
        if dataframe_length > 0:
            self._last_known_length = dataframe_length
        
        try:
            # 记录开始时间（用于性能监控）
            import time as time_module
            start_time = time_module.time()
            
            # 构建筛选条件 - 传入 current_df
            mask = self._build_pandas_filter(filters, df=current_df)
            
            # 检查 mask 是否有效
            if len(mask) != len(current_df):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"筛选掩码长度不匹配: mask={len(mask)}, dataframe={len(current_df)}. "
                    f"DataFrame索引: {current_df.index.tolist()[:10] if len(current_df) > 0 else 'empty'}, "
                    f"Mask索引: {mask.index.tolist()[:10] if len(mask) > 0 else 'empty'}"
                )
                # 重新创建正确的掩码，使用 DataFrame 的索引
                mask = pd.Series([True] * len(current_df), index=current_df.index)
            
            # 确保 mask 的索引与 dataframe 的索引匹配
            if not mask.index.equals(current_df.index):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"筛选掩码索引不匹配: 重新对齐索引. "
                    f"DataFrame索引范围: {current_df.index.min() if len(current_df) > 0 else 'N/A'} - "
                    f"{current_df.index.max() if len(current_df) > 0 else 'N/A'}, "
                    f"Mask索引范围: {mask.index.min() if len(mask) > 0 else 'N/A'} - "
                    f"{mask.index.max() if len(mask) > 0 else 'N/A'}"
                )
                # 重新创建掩码，确保索引匹配
                mask = pd.Series([True] * len(current_df), index=current_df.index)
            
            # 检查筛选后的数据量（用于调试）
            filtered_count = int(mask.sum()) if hasattr(mask, 'sum') else len(mask[mask])
            import logging
            logger = logging.getLogger(__name__)
            
            # 记录筛选信息（用于调试）
            filter_info = {}
            if filters:
                try:
                    filter_info = filters.model_dump(exclude_none=True) if hasattr(filters, 'model_dump') else (filters.dict(exclude_none=True) if hasattr(filters, 'dict') else {})
                except:
                    filter_info = str(filters)
            
            # 减少日志频率，仅在调试或异常时记录
            # logger.info(...)
            
            if filtered_count == 0 and len(current_df) > 0:
                logger.warning(
                    f"⚠️ 筛选后数据为空！原始数据量: {len(current_df)}, "
                    f"筛选条件: {filter_info}. 这可能导致表格显示为空！"
                )
            
            # 使用视图而不是copy，提高性能（在筛选时）
            filtered_df = current_df[mask]
            
            # 检查是否需要排序
            needs_sort = sort_by and sort_by in filtered_df.columns
            
            # 计算总数（在排序前，避免不必要的计算）
            total_count = len(filtered_df)
            
            # 排序（如果需要）
            if needs_sort:
                ascending = sort_order == 'ascending' if sort_order else True
                # 排序时需要copy，因为会修改数据
                filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending, na_position='last').copy()
            
            # 分页
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            # 确保索引范围有效
            if start_index >= total_count:
                # 请求的页面超出范围，返回空 DataFrame
                paginated_df = pd.DataFrame(columns=current_df.columns)
            else:
                # 确保 end_index 不超过总数
                end_index = min(end_index, total_count)
                # 只有在需要时才copy（如果已经copy过，这里就不需要再copy）
                if needs_sort:
                    paginated_df = filtered_df.iloc[start_index:end_index]
                else:
                    paginated_df = filtered_df.iloc[start_index:end_index].copy()
            
            # 记录性能信息（仅在大数据量时）
            elapsed_time = time_module.time() - start_time
            if elapsed_time > 0.5 or len(current_df) > 5000:
                logger.debug(
                    f"get_list 性能: 数据量={len(current_df)}, 筛选后={total_count}, "
                    f"分页={page}/{page_size}, 耗时={elapsed_time:.3f}秒"
                )
        except Exception as e:
            # 如果处理失败，记录错误并返回空结果
            import logging
            logger = logging.getLogger(__name__)
            dataframe_length = len(current_df) if current_df is not None else 'N/A'
            logger.error(
                f"get_list 处理失败: {str(e)}, dataframe长度={dataframe_length}, "
                f"dataframe是否为空={current_df.empty if current_df is not None else 'N/A'}, "
                f"筛选条件={filters.model_dump(exclude_none=True) if filters and hasattr(filters, 'model_dump') else (filters.dict(exclude_none=True) if filters and hasattr(filters, 'dict') else {})}",
                exc_info=True
            )
            # 如果 DataFrame 为空或不存在，返回空结果
            if current_df is None or current_df.empty:
                return {
                    "list": [],
                    "total": 0,
                    "page": page,
                    "pageSize": page_size
                }
            # 返回空 DataFrame，但保持正确的总数（用于分页显示）
            paginated_df = pd.DataFrame(columns=current_df.columns)
            # 尝试获取实际总数，如果失败则使用0
            try:
                total_count = len(current_df)
            except:
                total_count = 0
        
        # 将DataFrame转换为字典列表
        data_list = paginated_df.to_dict('records')
        
        # 处理特殊类型字段的转换
        for record in data_list:
            for key, value in record.items():
                if isinstance(value, bytes):
                    # 将bytes转换为16进制字符串，每个字节之间加空格
                    record[key] = ' '.join([f'{b:02X}' for b in value])
                elif key == 'ts' and isinstance(value, (int, float)):
                    # 将时间戳（float，微秒精度）转换为日期时间字符串
                    from datetime import datetime
                    try:
                        dt = datetime.fromtimestamp(float(value))
                        # 提取微秒部分（时间戳的小数部分转换为微秒）
                        microseconds = int((float(value) % 1) * 1000000)
                        record[key] = dt.strftime('%Y-%m-%d %H:%M:%S') + f'.{microseconds:06d}'
                    except (ValueError, OSError):
                        # 如果转换失败，保持原值
                        pass
        
        return {
            "list": data_list,
            "total": total_count,
            "page": page,
            "pageSize": page_size
        }
    
    def get_columns_config(self) -> Dict[str, Any]:
        """获取列配置信息
        
        Returns:
            包含columns配置的字典
        """
        # 将列配置转换为字典列表
        columns_list = []
        for col_config in self.columns_config:
            col_dict = {
                "prop": col_config.prop,
                "label": col_config.label,
                "type": col_config.type,
                "sortable": col_config.sortable,
                "filterable": col_config.filterable,
                "filterType": col_config.filterType,
                "minWidth": col_config.minWidth,
                "fixed": col_config.fixed,
            }
            if col_config.width is not None:
                col_dict["width"] = col_config.width
            if col_config.options is not None:
                col_dict["options"] = col_config.options
            columns_list.append(col_dict)
        
        return {
            "columns": columns_list
        }
    
    def get_row_position(self, row_id: Any, filters: Optional['FilterParams'] = None) -> Dict[str, Any]:
        """获取行在筛选结果中的位置
        
        Args:
            row_id: 行的ID值
            filters: 筛选条件
        
        Returns:
            包含found和position的字典
        """
        # 使用锁保护读取
        with self._lock:
            current_df = self.dataframe
            if current_df is None:
                return {"found": False, "position": -1}
        
        mask = self._build_pandas_filter(filters, df=current_df)
        filtered_df = current_df[mask].copy()
        
        # 查找选中行的位置
        matching_rows = filtered_df[filtered_df['id'] == row_id]
        if not matching_rows.empty:
            filtered_df_reset = filtered_df.reset_index(drop=True)
            matching_rows_reset = filtered_df_reset[filtered_df_reset['id'] == row_id]
            if not matching_rows_reset.empty:
                position = matching_rows_reset.index[0]
                return {
                    "found": True,
                    "position": int(position)
                }
        
        return {
            "found": False,
            "position": -1
        }
    
    def get_row_detail(self, row_id: Any) -> List[Dict[str, Any]]:
        """获取行的详细信息
        
        Args:
            row_id: 行的ID值
        
        Returns:
            行详情列表，每个元素包含label、value、detail、type等字段
        """
        # 使用锁保护读取
        with self._lock:
            current_df = self.dataframe
            if current_df is None:
                raise ValueError("DataFrame 未初始化")
        
        # 在DataFrame中通过ID列查找该行
        matching_rows = current_df[current_df['id'] == row_id]
        if len(matching_rows) == 0:
            raise ValueError(f"未找到ID为 {row_id} 的记录")
        
        row_record = matching_rows.iloc[0].to_dict()
        
        # 根据列配置生成详情
        detail = []
        for col_config in self.columns_config:
            prop = col_config.prop
            if prop in row_record:
                value = row_record[prop]
                # 处理特殊类型字段的转换
                if isinstance(value, bytes):
                    # 处理bytes类型字段，转换为16进制字符串用于JSON序列化
                    value = ' '.join([f'{b:02X}' for b in value])
                elif prop == 'ts' and isinstance(value, (int, float)):
                    # 将时间戳（float，微秒精度）转换为日期时间字符串
                    from datetime import datetime
                    try:
                        dt = datetime.fromtimestamp(float(value))
                        # 提取微秒部分（时间戳的小数部分转换为微秒）
                        microseconds = int((float(value) % 1) * 1000000)
                        value = dt.strftime('%Y-%m-%d %H:%M:%S') + f'.{microseconds:06d}'
                    except (ValueError, OSError):
                        # 如果转换失败，保持原值
                        pass
                
                detail_item = {
                    "label": col_config.label,
                    "value": value,
                    "detail": col_config.label,
                    "type": col_config.type
                }
                if col_config.type == 'number':
                    detail_item['format'] = 'int' if 'int' in str(current_df[prop].dtype) else 'float'
                detail.append(detail_item)
        
        return detail
    
    def update_dataframe(self, new_dataframe: pd.DataFrame) -> Dict[str, Any]:
        """直接更新DataFrame (由外部控制数据源时使用)
        
        Args:
            new_dataframe: 新的DataFrame数据
        
        Returns:
            包含更新结果的字典
        """
        # 使用锁保护写入
        with self._lock:
            if new_dataframe is None:
                raise ValueError("DataFrame不能为None")
            
            # 检查是否有新字段
            # 注意：这里假设 columns_config 已经包含了之前的所有字段
            existing_columns = set(c.prop for c in self.columns_config)
            new_columns = set(new_dataframe.columns)
            added_columns = new_columns - existing_columns
            
            columns_updated = False
            if added_columns:
                # 为新字段生成列配置
                temp_df = new_dataframe[list(added_columns)]
                new_columns_config = generate_columns_config_from_dataframe(temp_df)
                self.columns_config.extend(new_columns_config)
                columns_updated = True
            
            # 更新 DataFrame 引用
            self.dataframe = new_dataframe
            
            # 更新列配置中的筛选选项（对于 multi-select 和 select 类型）
            for col_config in self.columns_config:
                if col_config.filterType in ['multi-select', 'select']:
                    try:
                        # 检查该列是否存在于新数据中
                        if col_config.prop not in self.dataframe.columns:
                            continue
                            
                        # 性能优化：先检查唯一值数量
                        unique_count = self.dataframe[col_config.prop].nunique()
                        
                        if unique_count > 100:
                            if col_config.filterType != 'text':
                                col_config.options = None
                                col_config.filterType = 'text'
                                columns_updated = True
                        else:
                            unique_values = self.dataframe[col_config.prop].dropna().unique().tolist()
                            options = sorted([str(v) for v in unique_values])
                            
                            if col_config.options != options:
                                col_config.options = options
                                # options 变化需要通知前端刷新列配置，否则新出现的枚举值可能无法显示
                                columns_updated = True
                    except Exception:
                        pass
            
            # 验证列配置
            self._validate_columns()
            
            return {
                "success": True,
                "columns_updated": columns_updated,
                "total_count": len(self.dataframe)
            }

    def add_data(self, new_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Dict[str, Any]:
        """动态添加新数据到DataFrame
        
        Args:
            new_data: 新数据，可以是单个字典或字典列表
        
        Returns:
            包含添加结果和更新后的列配置的字典
        """
        # 使用锁保护写入
        with self._lock:
            # 检查 dataframe 是否有效
            if not hasattr(self, 'dataframe') or self.dataframe is None:
                raise ValueError("DataFrame 未初始化，无法添加数据")
            
            # 确保new_data是列表格式
            if isinstance(new_data, dict):
                new_data = [new_data]
            
            if not new_data:
                raise ValueError("新数据不能为空")
            
            # 保存原始数据量，用于验证
            original_length = len(self.dataframe)
            original_columns = set(self.dataframe.columns)
            
            # 转换为DataFrame
            new_df = pd.DataFrame(new_data)
            
            # 检查是否有新字段（不在现有DataFrame中的字段）
            existing_columns = set(self.dataframe.columns)
            new_columns = set(new_df.columns)
            added_columns = new_columns - existing_columns
            
            # 如果新数据中有新字段，需要更新列配置
            columns_updated = False
            if added_columns:
                # 为新字段生成列配置（generate_columns_config_from_dataframe 定义在本文件末尾）
                # 直接调用，无需导入
                
                # 创建一个临时DataFrame，只包含新字段，用于生成列配置
                temp_df = new_df[list(added_columns)]
                new_columns_config = generate_columns_config_from_dataframe(temp_df)
                
                # 将新列配置添加到现有配置中
                self.columns_config.extend(new_columns_config)
                columns_updated = True
            
            # 确保新数据的列与现有DataFrame的列对齐
            # 对于新数据中不存在的列，填充None
            for col in existing_columns:
                if col not in new_df.columns:
                    new_df[col] = None
            
            # 对于现有DataFrame中不存在的列（新字段），在现有DataFrame中填充None
            for col in added_columns:
                if col not in self.dataframe.columns:
                    self.dataframe[col] = None
            
            # 确保列顺序一致
            new_df = new_df[self.dataframe.columns]
            
            # 处理ID字段：如果新数据没有ID或ID为None，自动生成
            if 'id' in self.dataframe.columns:
                max_id = self.dataframe['id'].max() if len(self.dataframe) > 0 else 0
                for idx, row in new_df.iterrows():
                    if pd.isna(row.get('id')) or row.get('id') is None:
                        max_id += 1
                        new_df.at[idx, 'id'] = max_id
            
            # 处理特殊类型字段
            for col in new_df.columns:
                col_config = next((c for c in self.columns_config if c.prop == col), None)
                if col_config:
                    if col_config.type == 'bytes':
                        # 如果字段类型是bytes，但新数据是字符串，尝试转换
                        for idx, val in new_df[col].items():
                            if isinstance(val, str):
                                # 尝试将16进制字符串转换为bytes
                                try:
                                    # 移除空格并转换为bytes
                                    hex_str = val.replace(' ', '').replace('-', '')
                                    new_df.at[idx, col] = bytes.fromhex(hex_str)
                                except ValueError:
                                    # 如果转换失败，保持原值
                                    pass
                    elif col == 'ts' and col_config.type == 'date':
                        # 如果ts字段是字符串，尝试转换为时间戳
                        from datetime import datetime
                        for idx, val in new_df[col].items():
                            if pd.isna(val) or val is None:
                                continue
                            if isinstance(val, str) and val.strip():
                                try:
                                    # 尝试解析日期时间字符串（支持多种格式）
                                    val_stripped = val.strip()
                                    # 尝试完整格式：YYYY-MM-DD HH:MM:SS.ffffff
                                    try:
                                        dt = datetime.strptime(val_stripped, '%Y-%m-%d %H:%M:%S.%f')
                                        new_df.at[idx, col] = dt.timestamp()
                                    except ValueError:
                                        # 尝试格式：YYYY-MM-DD HH:MM:SS
                                        try:
                                            dt = datetime.strptime(val_stripped, '%Y-%m-%d %H:%M:%S')
                                            new_df.at[idx, col] = dt.timestamp()
                                        except ValueError:
                                            # 尝试格式：YYYY-MM-DD
                                            try:
                                                dt = datetime.strptime(val_stripped, '%Y-%m-%d')
                                                new_df.at[idx, col] = dt.timestamp()
                                            except ValueError:
                                                # 如果都失败，尝试作为数字（可能是时间戳字符串）
                                                try:
                                                    new_df.at[idx, col] = float(val_stripped)
                                                except ValueError:
                                                    pass
                                except Exception:
                                    pass
            
            # 将新数据追加到DataFrame
            # 使用 ignore_index=True 确保索引连续，避免索引问题
            # 注意：ignore_index=True 已经会重置索引，不需要再调用 reset_index
            try:
                # 执行合并操作
                combined_df = pd.concat([self.dataframe, new_df], ignore_index=True)
                
                # 验证合并后的数据量是否正确
                expected_length = original_length + len(new_df)
                if len(combined_df) != expected_length:
                    raise ValueError(
                        f"数据合并后长度不匹配: 期望 {expected_length}, 实际 {len(combined_df)}. "
                        f"原始数据量: {original_length}, 新数据量: {len(new_df)}"
                    )
                
                # 验证列是否一致
                if set(combined_df.columns) != original_columns:
                    missing_columns = original_columns - set(combined_df.columns)
                    if missing_columns:
                        raise ValueError(f"合并后缺少列: {missing_columns}")
                
                # 验证数据没有被清空（合并后的数据量应该大于等于原始数据量）
                if len(combined_df) < original_length:
                    raise ValueError(
                        f"数据合并后数据量减少: 原始 {original_length}, 合并后 {len(combined_df)}. "
                        f"这不应该发生，可能是数据被意外清空"
                    )
                
                # 所有验证通过后，才更新 self.dataframe
                self.dataframe = combined_df
                
                # 记录添加数据的信息
                import logging
                logger = logging.getLogger(__name__)
                logger.info(
                    f"add_data 成功: 添加了 {len(new_df)} 行, "
                    f"原始数据量={original_length}, 新数据量={len(self.dataframe)}"
                )
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                current_length = len(self.dataframe) if hasattr(self, 'dataframe') and self.dataframe is not None else 'N/A'
                logger.error(
                    f"添加数据失败: {str(e)}, 当前数据量={current_length}, "
                    f"新数据量={len(new_df)}, 原始数据量={original_length}",
                    exc_info=True
                )
                # 确保在异常情况下，dataframe 没有被破坏
                if not hasattr(self, 'dataframe') or self.dataframe is None or len(self.dataframe) < original_length:
                    logger.critical(
                        f"检测到 DataFrame 可能被破坏！原始数据量: {original_length}, "
                        f"当前数据量: {current_length}. 这可能导致数据丢失！"
                    )
                raise
            
            # 更新列配置中的筛选选项（对于 multi-select 和 select 类型）
            # 重新计算唯一值并更新 options
            for col_config in self.columns_config:
                if col_config.filterType in ['multi-select', 'select']:
                    try:
                        # 性能优化：先检查唯一值数量，如果太多直接切换为文本筛选，避免计算 unique()
                        # unique() 在数据量大时比较耗时
                        unique_count = self.dataframe[col_config.prop].nunique()
                        
                        if unique_count > 100:
                            # 如果超过100个，清空 options，使用文本筛选
                            if col_config.filterType != 'text':
                                col_config.options = None
                                col_config.filterType = 'text'
                                columns_updated = True
                        else:
                            # 获取该列的唯一值（数量不多，计算开销可接受）
                            unique_values = self.dataframe[col_config.prop].dropna().unique().tolist()
                            # 转换为字符串并排序
                            options = sorted([str(v) for v in unique_values])
                            
                            # 检查 options 是否有变化
                            if col_config.options != options:
                                col_config.options = options
                                # options 变化需要通知前端刷新列配置，否则新出现的枚举值可能无法显示
                                columns_updated = True
                                
                    except Exception as e:
                        # 如果更新失败，保持原有配置
                        pass
            
            # 验证列配置
            self._validate_columns()
            
            return {
                "success": True,
                "added_count": len(new_df),
                "columns_updated": columns_updated,
                "added_columns": list(added_columns) if added_columns else []
            }


def generate_columns_config_from_dataframe(df: pd.DataFrame) -> List[ColumnConfig]:
    """根据DataFrame自动生成列配置
    
    Args:
        df: pandas DataFrame
    
    Returns:
        列配置列表
    """
    columns_config = []
    
    for col in df.columns:
        col_type = str(df[col].dtype)
        column_type = 'string'
        filter_type = 'text'
        sortable = True
        filterable = True
        min_width = 120
        fixed = False
        options = None
        
        # 根据数据类型设置类型和筛选方式
        if col.lower() == 'ts':
            # ts字段优先识别为日期类型
            column_type = 'date'
            filter_type = 'date'
        elif 'int' in col_type or 'float' in col_type:
            column_type = 'number'
            filter_type = 'number'
        elif 'datetime' in col_type or 'date' in col.lower():
            # 自动识别日期字段（datetime类型、字段名包含date或ts字段）
            column_type = 'date'
            filter_type = 'date'
        elif col == 'id':
            # ID字段固定左侧，使用数字筛选
            filter_type = 'number'
            fixed = 'left'
        elif 'bytes' in col.lower() or 'hex' in col.lower() or 'remark' in col.lower() or 'payload' in col.lower():
            # 识别bytes类型字段（通过字段名识别）
            column_type = 'bytes'
            filter_type = 'text'  # bytes类型使用文本筛选
            min_width = 200  # bytes类型字段通常需要更宽的显示空间
        elif 'object' in col_type:
            # 检查是否为真正的bytes类型
            sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(sample_value, bytes):
                column_type = 'bytes'
                filter_type = 'text'
                min_width = 200
            else:
                # 不是bytes类型，检查是否为字符串类型，然后检查唯一值数量
                sample_values = df[col].dropna().head(10).tolist()
                is_hex_string = False
                if sample_values:
                    # 检查是否所有样本值都是16进制字符串格式（如 "FF 00 1A" 或 "FF001A"）
                    # 优化：增加长度限制，避免将普通长字符串误判为 hex
                    hex_pattern = re.compile(r'^([0-9A-Fa-f]{2}[\s]*)+$')
                    is_hex_string = all(
                        isinstance(v, str) and (hex_pattern.match(v.replace(' ', '')) or (len(v) > 20 and len(v) % 2 == 0 and all(c in '0123456789abcdefABCDEF ' for c in v)))
                        for v in sample_values if v
                    )
                    # 如果字段名包含相关关键词，也认为是bytes类型
                    if is_hex_string or any(keyword in col.lower() for keyword in ['bytes', 'hex', 'binary', 'data', 'payload']):
                        column_type = 'bytes'
                        filter_type = 'text'
                        min_width = 200
                    else:
                        # 启发式规则：如果是 ID、编号、Code 等字段，通常是高基数的，直接使用文本筛选
                        # 避免一开始误判为 multi-select
                        is_id_like = any(keyword in col.lower() for keyword in ['id', 'no', 'number', 'code', 'uuid', 'guid'])
                        
                        if is_id_like:
                            filter_type = 'text'
                        else:
                            unique_values = df[col].unique().tolist()
                            if len(unique_values) <= 100:  # 如果唯一值少于100个，提供下拉选项
                                filter_type = 'multi-select'
                                options = [str(v) for v in unique_values]
                            else:
                                # 唯一值太多，使用文本筛选
                                filter_type = 'text'
                else:
                    filter_type = 'text'
        else:
            # 对于字符串类型，检查唯一值数量
            if 'string' in col_type:
                # 检查数据内容是否看起来像16进制字符串（bytes的常见表示形式）
                sample_values = df[col].dropna().head(10).tolist()
                is_hex_string = False
                if sample_values:
                    # 检查是否所有样本值都是16进制字符串格式（如 "FF 00 1A" 或 "FF001A"）
                    # 优化：增加长度限制，避免将普通长字符串误判为 hex
                    hex_pattern = re.compile(r'^([0-9A-Fa-f]{2}[\s]*)+$')
                    is_hex_string = all(
                        isinstance(v, str) and (hex_pattern.match(v.replace(' ', '')) or (len(v) > 20 and len(v) % 2 == 0 and all(c in '0123456789abcdefABCDEF ' for c in v)))
                        for v in sample_values if v
                    )
                    # 如果字段名包含相关关键词，也认为是bytes类型
                    if is_hex_string or any(keyword in col.lower() for keyword in ['bytes', 'hex', 'binary', 'data', 'payload']):
                        column_type = 'bytes'
                        filter_type = 'text'
                        min_width = 200
                    else:
                        # 启发式规则：如果是 ID、编号、Code 等字段，通常是高基数的，直接使用文本筛选
                        is_id_like = any(keyword in col.lower() for keyword in ['id', 'no', 'number', 'code', 'uuid', 'guid'])
                        
                        if is_id_like:
                            filter_type = 'text'
                        else:
                            unique_values = df[col].unique().tolist()
                            if len(unique_values) <= 100:  # 如果唯一值少于100个，提供下拉选项
                                filter_type = 'multi-select'
                                options = [str(v) for v in unique_values]
                            else:
                                # 唯一值太多，使用文本筛选
                                filter_type = 'text'
                else:
                    filter_type = 'text'
            else:
                filter_type = 'text'
        
        columns_config.append(ColumnConfig(
            prop=col,
            label=col,
            type=column_type,
            sortable=sortable,
            filterable=filterable,
            filterType=filter_type,
            minWidth=min_width,
            fixed=fixed,
            options=options
        ))
    
    return columns_config

