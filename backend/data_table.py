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
            dataframe: pandas DataFrame格式的数据
            columns_config: 列配置列表，定义每列的属性（字段名、类型、筛选方式等）
        """
        if dataframe is None or dataframe.empty:
            raise ValueError("DataFrame不能为空")
        if not columns_config:
            raise ValueError("列配置不能为空")
        
        self.dataframe = dataframe.copy()
        self.columns_config = columns_config
        # 验证列配置中的字段是否存在于DataFrame中
        self._validate_columns()
    
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
    
    def _build_pandas_filter(self, filters: Optional['FilterParams'] = None) -> pd.Series:
        """将筛选条件转换为pandas布尔索引（动态处理任意字段）"""
        # 延迟导入避免循环依赖
        try:
            from .api import FilterParams, FilterGroup, NumberFilter  # type: ignore
        except ImportError:
            from backend.api import FilterParams, FilterGroup, NumberFilter  # type: ignore
        
        if not filters:
            return pd.Series([True] * len(self.dataframe))
        
        # 初始化筛选掩码
        mask = pd.Series([True] * len(self.dataframe))
        
        # 获取筛选参数字典
        filter_dict = filters.model_dump(exclude_none=True) if hasattr(filters, 'model_dump') else filters.dict(exclude_none=True) if hasattr(filters, 'dict') else {}
        
        # 遍历所有筛选字段（包括动态字段和旧字段）
        for field_name, filter_value in filter_dict.items():
            
            # 检查字段是否存在于DataFrame中
            if field_name not in self.dataframe.columns:
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
                                filters_mask.append(self.dataframe[field_name] == val)
                            elif op == '>':
                                filters_mask.append(self.dataframe[field_name] > val)
                            elif op == '<':
                                filters_mask.append(self.dataframe[field_name] < val)
                            elif op == '>=':
                                filters_mask.append(self.dataframe[field_name] >= val)
                            elif op == '<=':
                                filters_mask.append(self.dataframe[field_name] <= val)
                    
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
                                mask &= (self.dataframe[field_name] == val)
                            elif op == '>':
                                mask &= (self.dataframe[field_name] > val)
                            elif op == '<':
                                mask &= (self.dataframe[field_name] < val)
                            elif op == '>=':
                                mask &= (self.dataframe[field_name] >= val)
                            elif op == '<=':
                                mask &= (self.dataframe[field_name] <= val)
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
                                    filters_mask.append(self.dataframe[field_name] == val)
                                elif op == '>':
                                    filters_mask.append(self.dataframe[field_name] > val)
                                elif op == '<':
                                    filters_mask.append(self.dataframe[field_name] < val)
                                elif op == '>=':
                                    filters_mask.append(self.dataframe[field_name] >= val)
                                elif op == '<=':
                                    filters_mask.append(self.dataframe[field_name] <= val)
                        
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
                                    mask &= (self.dataframe[field_name] == val)
                                elif op == '>':
                                    mask &= (self.dataframe[field_name] > val)
                                elif op == '<':
                                    mask &= (self.dataframe[field_name] < val)
                                elif op == '>=':
                                    mask &= (self.dataframe[field_name] >= val)
                                elif op == '<=':
                                    mask &= (self.dataframe[field_name] <= val)
            
            elif col_config.filterType == 'text':
                # 文本筛选
                if isinstance(filter_value, str) and filter_value:
                    # 对于bytes类型字段，需要先转换为16进制字符串再筛选
                    if col_config.type == 'bytes':
                        # 将bytes转换为16进制字符串进行筛选
                        def bytes_to_hex_str(val):
                            if isinstance(val, bytes):
                                return ' '.join([f'{b:02X}' for b in val])
                            return str(val)
                        hex_series = self.dataframe[field_name].apply(bytes_to_hex_str)
                        mask &= hex_series.str.contains(filter_value, case=False, na=False)
                    else:
                        mask &= self.dataframe[field_name].astype(str).str.contains(filter_value, case=False, na=False)
            
            elif col_config.filterType == 'date':
                # 日期筛选
                if isinstance(filter_value, str) and filter_value:
                    mask &= (self.dataframe[field_name].astype(str) == filter_value)
            
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
                        mask &= self.dataframe[field_name].isin(filter_list)
                    except Exception as e:
                        # 尝试转换为字符串后再筛选
                        try:
                            mask &= self.dataframe[field_name].astype(str).isin([str(v) for v in filter_list])
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
        # 构建筛选条件
        mask = self._build_pandas_filter(filters)
        filtered_df = self.dataframe[mask].copy()
        
        # 排序
        if sort_by and sort_by in filtered_df.columns:
            ascending = sort_order == 'ascending' if sort_order else True
            filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending, na_position='last')
        
        # 计算总数
        total_count = len(filtered_df)
        
        # 分页
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_df = filtered_df.iloc[start_index:end_index]
        
        # 将DataFrame转换为字典列表
        data_list = paginated_df.to_dict('records')
        
        # 处理bytes类型字段，转换为16进制字符串用于JSON序列化
        for record in data_list:
            for key, value in record.items():
                if isinstance(value, bytes):
                    # 将bytes转换为16进制字符串，每个字节之间加空格
                    record[key] = ' '.join([f'{b:02X}' for b in value])
        
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
        mask = self._build_pandas_filter(filters)
        filtered_df = self.dataframe[mask].copy()
        
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
        # 在DataFrame中通过ID列查找该行
        matching_rows = self.dataframe[self.dataframe['id'] == row_id]
        if len(matching_rows) == 0:
            raise ValueError(f"未找到ID为 {row_id} 的记录")
        
        row_record = matching_rows.iloc[0].to_dict()
        
        # 根据列配置生成详情
        detail = []
        for col_config in self.columns_config:
            prop = col_config.prop
            if prop in row_record:
                value = row_record[prop]
                # 处理bytes类型字段，转换为16进制字符串用于JSON序列化
                if isinstance(value, bytes):
                    value = ' '.join([f'{b:02X}' for b in value])
                
                detail_item = {
                    "label": col_config.label,
                    "value": value,
                    "detail": col_config.label,
                    "type": col_config.type
                }
                if col_config.type == 'number':
                    detail_item['format'] = 'int' if 'int' in str(self.dataframe[prop].dtype) else 'float'
                detail.append(detail_item)
        
        return detail


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
        if 'int' in col_type or 'float' in col_type:
            column_type = 'number'
            filter_type = 'number'
        elif 'datetime' in col_type or 'date' in col.lower():
            # 自动识别日期字段（datetime类型或字段名包含date）
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
                    hex_pattern = re.compile(r'^([0-9A-Fa-f]{2}[\s]*)+$')
                    is_hex_string = all(
                        isinstance(v, str) and (hex_pattern.match(v.replace(' ', '')) or len(v) > 20)
                        for v in sample_values if v
                    )
                    # 如果字段名包含相关关键词，也认为是bytes类型
                    if is_hex_string or any(keyword in col.lower() for keyword in ['bytes', 'hex', 'binary', 'data']):
                        column_type = 'bytes'
                        filter_type = 'text'
                        min_width = 200
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
                    hex_pattern = re.compile(r'^([0-9A-Fa-f]{2}[\s]*)+$')
                    is_hex_string = all(
                        isinstance(v, str) and (hex_pattern.match(v.replace(' ', '')) or len(v) > 20)
                        for v in sample_values if v
                    )
                    # 如果字段名包含相关关键词，也认为是bytes类型
                    if is_hex_string or any(keyword in col.lower() for keyword in ['bytes', 'hex', 'binary', 'data']):
                        column_type = 'bytes'
                        filter_type = 'text'
                        min_width = 200
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

