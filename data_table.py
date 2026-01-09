"""DataTable类 - 表格数据管理类

封装表格的数据处理功能，包括筛选、分页、排序等操作。
初始化时传入DataFrame格式的数据和列配置。
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union, Tuple
import pandas as pd
import re
import logging
from datetime import datetime


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


# 数据模型（从 api.py 移过来，避免循环导入）
class NumberFilter(BaseModel):
    """数字筛选条件"""
    operator: Optional[str] = None  # '=', '>', '<', '>=', '<=' 
    value: Optional[Union[int, float, str]] = None  # 支持整数、浮点数和字符串（支持16进制如0x123）


class FilterGroup(BaseModel):
    """筛选条件组（多个条件组合）"""
    filters: List[NumberFilter]
    logic: Optional[str] = 'AND'  # 'AND' 或 'OR'


class FilterParams(BaseModel):
    """动态筛选参数，支持任意字段名"""
    model_config = {"extra": "allow"}  # 允许额外字段


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
    
    @property
    def _logger(self):
        """获取日志记录器"""
        return logging.getLogger(__name__)
    
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
    
    def _bytes_to_hex(self, value: bytes) -> str:
        """将bytes转换为16进制字符串，每个字节之间加空格"""
        return ' '.join([f'{b:02X}' for b in value])
    
    def _timestamp_to_str(self, ts: Union[int, float]) -> str:
        """将时间戳转换为日期时间字符串"""
        try:
            dt = datetime.fromtimestamp(float(ts))
            microseconds = int((float(ts) % 1) * 1000000)
            return dt.strftime('%Y-%m-%d %H:%M:%S') + f'.{microseconds:06d}'
        except (ValueError, OSError):
            return str(ts)
    
    def _apply_number_operator(self, df_series: pd.Series, operator: str, value: Union[int, float]) -> pd.Series:
        """应用数字操作符到pandas Series"""
        if operator == '=':
            return df_series == value
        elif operator == '>':
            return df_series > value
        elif operator == '<':
            return df_series < value
        elif operator == '>=':
            return df_series >= value
        elif operator == '<=':
            return df_series <= value
        else:
            return pd.Series([True] * len(df_series), index=df_series.index)
    
    def _process_number_filter(self, filter_value: Any, field_name: str, target_df: pd.DataFrame) -> Optional[pd.Series]:
        """处理数字筛选条件，返回筛选掩码或None"""
        # 统一处理 FilterGroup、NumberFilter 和字典格式
        filter_group = None
        if isinstance(filter_value, FilterGroup):
            filter_group = filter_value
        elif isinstance(filter_value, NumberFilter):
            # 单个 NumberFilter 转换为 FilterGroup
            filter_group = FilterGroup(filters=[filter_value], logic='AND')
        elif isinstance(filter_value, dict):
            if 'filters' in filter_value:
                filter_group = FilterGroup(**filter_value)
            elif 'operator' in filter_value or 'value' in filter_value:
                filter_group = FilterGroup(filters=[NumberFilter(**filter_value)], logic='AND')
        
        if not filter_group:
            return None
        
        filters_mask = []
        for num_filter in filter_group.filters:
            if num_filter.operator and num_filter.value is not None:
                val = self._parse_number_value(num_filter.value)
                if val is not None:
                    filters_mask.append(self._apply_number_operator(target_df[field_name], num_filter.operator, val))
        
        if not filters_mask:
            return None
        
        # 组合多个条件
        logic = filter_group.logic or 'AND'
        if logic.upper() == 'OR':
            field_mask = filters_mask[0]
            for m in filters_mask[1:]:
                field_mask |= m
        else:
            field_mask = filters_mask[0]
            for m in filters_mask[1:]:
                field_mask &= m
        
        return field_mask
    
    def _get_filter_dict(self, filters: Optional[Any]) -> Dict[str, Any]:
        """获取筛选参数字典，支持 Pydantic 模型和普通字典，确保包含额外字段"""
        if not filters:
            return {}
        
        if isinstance(filters, dict):
            return filters
            
        res = {}
        
        # 1. 尝试使用 Pydantic v2 的 model_dump
        if hasattr(filters, 'model_dump'):
            try:
                res.update(filters.model_dump(exclude_none=True))
            except Exception:
                pass
        # 尝试使用 Pydantic v1 的 dict
        elif hasattr(filters, 'dict'):
            try:
                res.update(filters.dict(exclude_none=True))
            except Exception:
                pass
        
        # 2. 关键：获取 Pydantic v2 的额外字段 (extra="allow")
        if hasattr(filters, 'model_extra') and filters.model_extra:
            res.update(filters.model_extra)
            
        # 3. 兜底方案：从 __dict__ 中提取非私有属性
        for k, v in filters.__dict__.items():
            if k not in res and not k.startswith('_') and k != 'model_config' and k != 'model_fields':
                res[k] = v
        
        return res
    
    def _update_column_options(self, force: bool = False) -> bool:
        """更新列配置中的筛选选项（对于 multi-select 和 select 类型），返回是否有更新"""
        # 如果不是强制更新，且数据量变化不大（小于5%），则跳过以提高性能
        if not force and hasattr(self, '_last_options_update_len'):
            current_len = len(self.dataframe)
            if current_len > 0 and (current_len - self._last_options_update_len) / current_len < 0.05:
                return False

        columns_updated = False
        for col_config in self.columns_config:
            if col_config.filterType in ['multi-select', 'select']:
                try:
                    if col_config.prop not in self.dataframe.columns:
                        continue
                    
                    # 使用 sample 提高性能，或者直接计算 nunique
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
                            columns_updated = True
                except Exception:
                    pass
        
        self._last_options_update_len = len(self.dataframe)
        return columns_updated
    
    def _build_pandas_filter(self, filters: Optional[FilterParams] = None, df: Optional[pd.DataFrame] = None) -> pd.Series:
        """将筛选条件转换为pandas布尔索引（动态处理任意字段）"""
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
        filter_dict = self._get_filter_dict(filters)
        
        # 遍历所有筛选字段（包括动态字段和旧字段）
        for field_name, filter_value in filter_dict.items():
            
            # 检查字段是否存在于DataFrame中
            if field_name not in target_df.columns:
                continue
            
            # 查找对应的列配置
            col_config = next((c for c in self.columns_config if c.prop == field_name), None)
            if not col_config:
                continue
                
            if not col_config.filterable:
                continue
            
            # 根据筛选类型处理
            if col_config.filterType == 'number':
                # 数字类型筛选
                field_mask = self._process_number_filter(filter_value, field_name, target_df)
                if field_mask is not None:
                    mask &= field_mask
            
            elif col_config.filterType == 'text':
                # 文本筛选
                if isinstance(filter_value, str) and filter_value:
                    # 对于bytes类型字段，需要先转换为16进制字符串再筛选
                    if col_config.type == 'bytes':
                        try:
                            if target_df[field_name].dtype == 'object':
                                sample = target_df[field_name].dropna()
                                if len(sample) > 0 and isinstance(sample.iloc[0], bytes):
                                    hex_series = target_df[field_name].apply(
                                        lambda val: self._bytes_to_hex(val) if isinstance(val, bytes) else str(val)
                                    )
                                    mask &= hex_series.str.contains(filter_value, case=False, na=False)
                                else:
                                    mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                            else:
                                mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                        except Exception:
                            mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                    else:
                        mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
            
            elif col_config.filterType == 'date':
                # 日期筛选
                if isinstance(filter_value, str) and filter_value:
                    if field_name == 'ts':
                        try:
                            ts_str_series = target_df[field_name].apply(self._timestamp_to_str)
                            mask &= ts_str_series.str.contains(filter_value, case=False, na=False)
                        except Exception:
                            mask &= target_df[field_name].astype(str).str.contains(filter_value, case=False, na=False)
                    else:
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
        """获取数据列表（支持筛选、分页、排序）"""
        # 使用锁保护读取，并创建dataframe快照以确保操作的一致性
        with self._lock:
            current_df = self.dataframe
            if current_df is None:
                return {
                    "list": [], "total": 0, "page": page, "pageSize": page_size
                }
        
        if current_df.empty:
            return {
                "list": [], "total": 0, "page": page, "pageSize": page_size
            }
        
        try:
            # 构建筛选条件
            mask = self._build_pandas_filter(filters, df=current_df)
            
            # 确保 mask 的索引与 dataframe 的索引匹配
            if not mask.index.equals(current_df.index):
                mask = pd.Series([True] * len(current_df), index=current_df.index)
            
            # 使用视图而不是copy，提高性能（在筛选时）
            filtered_df = current_df[mask]
            
            # 检查是否需要排序
            needs_sort = sort_by and sort_by in filtered_df.columns
            
            # 计算总数
            total_count = len(filtered_df)
            
            # 排序
            if needs_sort:
                ascending = sort_order == 'ascending' if sort_order else True
                filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending, na_position='last')
            
            # 分页
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            if start_index >= total_count:
                paginated_df = pd.DataFrame(columns=current_df.columns)
            else:
                end_index = min(end_index, total_count)
                paginated_df = filtered_df.iloc[start_index:end_index]
            
            # 将DataFrame转换为字典列表
            data_list = paginated_df.to_dict('records')
            
            # 处理特殊类型字段的转换
            for record in data_list:
                for key, value in record.items():
                    if isinstance(value, bytes):
                        record[key] = self._bytes_to_hex(value)
                    elif key == 'ts' and isinstance(value, (int, float)):
                        record[key] = self._timestamp_to_str(value)
            
            return {
                "list": data_list,
                "total": total_count,
                "page": page,
                "pageSize": page_size
            }
        except Exception as e:
            self._logger.error(f"get_list 处理失败: {str(e)}", exc_info=True)
            return {
                "list": [],
                "total": 0,
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息
        
        Returns:
            包含统计数据的字典（行列格式）
        """
        with self._lock:
            current_df = self.dataframe
            columns_config = self.columns_config
            
        total_rows = len(current_df)
        total_columns = len(columns_config)
        
        # 获取列名列表
        column_names = [col.label for col in columns_config]
        
        # 获取可筛选列数量
        filterable_columns = sum(1 for col in columns_config if col.filterable)
        
        # 获取可排序列数量
        sortable_columns = sum(1 for col in columns_config if col.sortable)
        
        # 构建统计数据
        statistics_data = {
            "columns": ["统计项", "值", "描述"],
            "rows": [
                {"统计项": "总行数", "值": str(total_rows), "描述": "数据表中的总记录数"},
                {"统计项": "总列数", "值": str(total_columns), "描述": "数据表中的总列数"},
                {"统计项": "可筛选列数", "值": str(filterable_columns), "描述": "支持筛选功能的列数"},
                {"统计项": "可排序列数", "值": str(sortable_columns), "描述": "支持排序功能的列数"},
                {"统计项": "列名列表", "值": ", ".join(column_names[:5]) + ("..." if len(column_names) > 5 else ""), "描述": "所有列的名称"},
            ]
        }
        
        return statistics_data
    
    def get_row_position(self, 
                         row_id: Any, 
                         filters: Optional['FilterParams'] = None,
                         sort_by: Optional[str] = None,
                         sort_order: Optional[str] = None) -> Dict[str, Any]:
        """获取行在筛选结果中的位置（支持排序）
        
        Args:
            row_id: 行的ID值
            filters: 筛选条件
            sort_by: 排序字段
            sort_order: 排序方向
        
        Returns:
            包含found和position的字典
        """
        # 使用锁保护读取
        with self._lock:
            current_df = self.dataframe
            if current_df is None:
                return {"found": False, "position": -1}
        
        mask = self._build_pandas_filter(filters, df=current_df)
        filtered_df = current_df[mask]
        
        if filtered_df.empty:
            return {"found": False, "position": -1}

        # 排序（如果需要）
        if sort_by and sort_by in filtered_df.columns:
            ascending = sort_order == 'ascending' if sort_order else True
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending, na_position='last')
        
        # 查找选中行的位置
        # 重置索引以便获取当前排序下的绝对位置
        filtered_df_reset = filtered_df.reset_index(drop=True)
        matching_indices = filtered_df_reset.index[filtered_df_reset['id'] == row_id].tolist()
        
        if matching_indices:
            return {
                "found": True,
                "position": int(matching_indices[0])
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
                    value = self._bytes_to_hex(value)
                elif prop == 'ts' and isinstance(value, (int, float)):
                    value = self._timestamp_to_str(value)
                
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
            removed_columns = existing_columns - new_columns
            
            columns_updated = False
            if added_columns:
                # 为新字段生成列配置
                temp_df = new_dataframe[list(added_columns)]
                new_columns_config = generate_columns_config_from_dataframe(temp_df)
                self.columns_config.extend(new_columns_config)
                columns_updated = True
            
            # 移除已删除的列的配置
            if removed_columns:
                self.columns_config = [c for c in self.columns_config if c.prop not in removed_columns]
                columns_updated = True
            
            # 更新 DataFrame 引用
            self.dataframe = new_dataframe
            
            structure_updated = bool(added_columns or removed_columns)
            
            # 按照 new_dataframe.columns 的顺序重新排列列配置
            # 创建一个字典，方便快速查找列配置
            config_dict = {c.prop: c for c in self.columns_config}
            # 按照 new_dataframe.columns 的顺序重新构建列配置列表
            reordered_config = []
            for col_name in new_dataframe.columns:
                if col_name in config_dict:
                    reordered_config.append(config_dict[col_name])
                else:
                    # 如果列配置不存在（理论上不应该发生），生成一个新的
                    self._logger.warning(f"列 {col_name} 在列配置中不存在，自动生成配置")
                    temp_df = new_dataframe[[col_name]]
                    new_config = generate_columns_config_from_dataframe(temp_df)
                    if new_config:
                        reordered_config.append(new_config[0])
                        structure_updated = True
            
            # 检查顺序是否改变
            if not structure_updated and [c.prop for c in self.columns_config] != [c.prop for c in reordered_config]:
                structure_updated = True
            
            # 更新列配置列表
            self.columns_config = reordered_config
            
            # 更新列配置中的筛选选项
            options_updated = self._update_column_options(force=True)
            
            # 验证列配置
            self._validate_columns()
            
            return {
                "success": True,
                "structure_updated": structure_updated,
                "options_updated": options_updated,
                "columns_updated": structure_updated or options_updated,  # 保持兼容性
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
                
            except Exception as e:
                raise
            
            # 更新列配置中的筛选选项
            options_updated = self._update_column_options(force=False)
            
            # 验证列配置
            self._validate_columns()
            
            structure_updated = bool(added_columns)
            
            return {
                "success": True,
                "added_count": len(new_df),
                "structure_updated": structure_updated,
                "options_updated": options_updated,
                "columns_updated": structure_updated or options_updated,  # 保持兼容性
                "added_columns": list(added_columns) if added_columns else []
            }


def _is_hex_string(sample_values: List[Any], col_name: str) -> bool:
    """检查样本值是否都是16进制字符串格式"""
    if not sample_values:
        return False
    
    hex_pattern = re.compile(r'^([0-9A-Fa-f]{2}[\s]*)+$')
    is_hex = all(
        isinstance(v, str) and (
            hex_pattern.match(v.replace(' ', '')) or 
            (len(v) > 20 and len(v) % 2 == 0 and all(c in '0123456789abcdefABCDEF ' for c in v))
        )
        for v in sample_values if v
    )
    
    # 如果字段名包含相关关键词，也认为是bytes类型
    return is_hex or any(keyword in col_name.lower() for keyword in ['bytes', 'hex', 'binary', 'data', 'payload'])


def _determine_string_column_type(df: pd.DataFrame, col: str, col_type: str) -> Tuple[str, str, int]:
    """确定字符串类型列的配置（column_type, filter_type, min_width）"""
    sample_values = df[col].dropna().head(10).tolist()
    
    # 检查是否为16进制字符串（bytes类型）
    if _is_hex_string(sample_values, col):
        return 'bytes', 'text', 200
    
    # 启发式规则：如果是 ID、编号、Code 等字段，通常是高基数的，直接使用文本筛选
    is_id_like = any(keyword in col.lower() for keyword in ['id', 'no', 'number', 'code', 'uuid', 'guid'])
    if is_id_like:
        return 'string', 'text', 120
    
    # 检查唯一值数量
    unique_values = df[col].unique().tolist()
    if len(unique_values) <= 100:
        return 'string', 'multi-select', 120
    else:
        return 'string', 'text', 120


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
            column_type = 'date'
            filter_type = 'date'
        elif 'int' in col_type or 'float' in col_type:
            column_type = 'number'
            filter_type = 'number'
        elif 'datetime' in col_type or 'date' in col.lower():
            column_type = 'date'
            filter_type = 'date'
        elif col == 'id':
            filter_type = 'number'
            fixed = 'left'
        elif 'bytes' in col.lower() or 'hex' in col.lower() or 'remark' in col.lower() or 'payload' in col.lower():
            column_type = 'bytes'
            filter_type = 'text'
            min_width = 200
        elif 'object' in col_type:
            sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            if isinstance(sample_value, bytes):
                column_type = 'bytes'
                filter_type = 'text'
                min_width = 200
            else:
                column_type, filter_type, min_width = _determine_string_column_type(df, col, col_type)
                if filter_type == 'multi-select':
                    unique_values = df[col].unique().tolist()
                    options = [str(v) for v in unique_values]
        elif 'string' in col_type:
            column_type, filter_type, min_width = _determine_string_column_type(df, col, col_type)
            if filter_type == 'multi-select':
                unique_values = df[col].unique().tolist()
                options = [str(v) for v in unique_values]
        
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

