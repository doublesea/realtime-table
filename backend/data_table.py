"""DataTable类 - 表格数据管理类

封装表格的数据处理功能，包括筛选、分页、排序等操作。
初始化时传入DataFrame格式的数据和列配置。
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd


class ColumnConfig(BaseModel):
    """列配置模型"""
    prop: str  # 字段名
    label: str  # 列标题
    type: str  # 数据类型: 'string', 'number', 'date', 'boolean'
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
    
    def _build_pandas_filter(self, filters: Optional['FilterParams'] = None) -> pd.Series:
        """将筛选条件转换为pandas布尔索引"""
        # 延迟导入避免循环依赖
        try:
            from .api import FilterParams, FilterGroup  # type: ignore
        except ImportError:
            from backend.api import FilterParams, FilterGroup  # type: ignore
        
        if not filters:
            return pd.Series([True] * len(self.dataframe))
        
        # 初始化筛选掩码
        mask = pd.Series([True] * len(self.dataframe))
        
        # ID筛选
        if filters.id:
            if isinstance(filters.id, FilterGroup):
                id_filters_mask = []
                for id_filter in filters.id.filters:
                    if id_filter.operator and id_filter.value is not None:
                        if id_filter.operator == '=':
                            id_filters_mask.append(self.dataframe['id'] == id_filter.value)
                        elif id_filter.operator == '>':
                            id_filters_mask.append(self.dataframe['id'] > id_filter.value)
                        elif id_filter.operator == '<':
                            id_filters_mask.append(self.dataframe['id'] < id_filter.value)
                        elif id_filter.operator == '>=':
                            id_filters_mask.append(self.dataframe['id'] >= id_filter.value)
                        elif id_filter.operator == '<=':
                            id_filters_mask.append(self.dataframe['id'] <= id_filter.value)
                
                if id_filters_mask:
                    logic = getattr(filters.id, 'logic', 'AND')
                    if logic and logic.upper() == 'OR':
                        id_mask = id_filters_mask[0]
                        for m in id_filters_mask[1:]:
                            id_mask |= m
                        mask &= id_mask
                    else:
                        id_mask = id_filters_mask[0]
                        for m in id_filters_mask[1:]:
                            id_mask &= m
                        mask &= id_mask
            else:
                if filters.id.operator and filters.id.value is not None:
                    if filters.id.operator == '=':
                        mask &= (self.dataframe['id'] == filters.id.value)
                    elif filters.id.operator == '>':
                        mask &= (self.dataframe['id'] > filters.id.value)
                    elif filters.id.operator == '<':
                        mask &= (self.dataframe['id'] < filters.id.value)
                    elif filters.id.operator == '>=':
                        mask &= (self.dataframe['id'] >= filters.id.value)
                    elif filters.id.operator == '<=':
                        mask &= (self.dataframe['id'] <= filters.id.value)
        
        # 文本筛选
        if filters.name:
            mask &= self.dataframe['name'].str.contains(filters.name, case=False, na=False)
        if filters.email:
            mask &= self.dataframe['email'].str.contains(filters.email, case=False, na=False)
        
        # 部门筛选（支持单选或多选）
        if filters.department:
            if isinstance(filters.department, list):
                mask &= self.dataframe['department'].isin(filters.department)
            else:
                mask &= (self.dataframe['department'] == filters.department)
        
        # 状态筛选（支持单选或多选）
        if filters.status:
            if isinstance(filters.status, list):
                mask &= self.dataframe['status'].isin(filters.status)
            else:
                mask &= (self.dataframe['status'] == filters.status)
        
        # 年龄筛选
        if filters.age:
            if isinstance(filters.age, FilterGroup):
                age_filters_mask = []
                for age_filter in filters.age.filters:
                    if age_filter.operator and age_filter.value is not None:
                        if age_filter.operator == '=':
                            age_filters_mask.append(self.dataframe['age'] == age_filter.value)
                        elif age_filter.operator == '>':
                            age_filters_mask.append(self.dataframe['age'] > age_filter.value)
                        elif age_filter.operator == '<':
                            age_filters_mask.append(self.dataframe['age'] < age_filter.value)
                        elif age_filter.operator == '>=':
                            age_filters_mask.append(self.dataframe['age'] >= age_filter.value)
                        elif age_filter.operator == '<=':
                            age_filters_mask.append(self.dataframe['age'] <= age_filter.value)
                
                if age_filters_mask:
                    logic = getattr(filters.age, 'logic', 'AND')
                    if logic and logic.upper() == 'OR':
                        age_mask = age_filters_mask[0]
                        for m in age_filters_mask[1:]:
                            age_mask |= m
                        mask &= age_mask
                    else:
                        age_mask = age_filters_mask[0]
                        for m in age_filters_mask[1:]:
                            age_mask &= m
                        mask &= age_mask
            else:
                if filters.age.operator and filters.age.value is not None:
                    if filters.age.operator == '=':
                        mask &= (self.dataframe['age'] == filters.age.value)
                    elif filters.age.operator == '>':
                        mask &= (self.dataframe['age'] > filters.age.value)
                    elif filters.age.operator == '<':
                        mask &= (self.dataframe['age'] < filters.age.value)
                    elif filters.age.operator == '>=':
                        mask &= (self.dataframe['age'] >= filters.age.value)
                    elif filters.age.operator == '<=':
                        mask &= (self.dataframe['age'] <= filters.age.value)
        elif filters.ageMin is not None:
            mask &= (self.dataframe['age'] >= filters.ageMin)
        elif filters.ageMax is not None:
            mask &= (self.dataframe['age'] <= filters.ageMax)
        
        # 薪资筛选
        if filters.salary:
            if isinstance(filters.salary, FilterGroup):
                salary_filters_mask = []
                for salary_filter in filters.salary.filters:
                    if salary_filter.operator and salary_filter.value is not None:
                        if salary_filter.operator == '=':
                            salary_filters_mask.append(self.dataframe['salary'] == salary_filter.value)
                        elif salary_filter.operator == '>':
                            salary_filters_mask.append(self.dataframe['salary'] > salary_filter.value)
                        elif salary_filter.operator == '<':
                            salary_filters_mask.append(self.dataframe['salary'] < salary_filter.value)
                        elif salary_filter.operator == '>=':
                            salary_filters_mask.append(self.dataframe['salary'] >= salary_filter.value)
                        elif salary_filter.operator == '<=':
                            salary_filters_mask.append(self.dataframe['salary'] <= salary_filter.value)
                
                if salary_filters_mask:
                    logic = getattr(filters.salary, 'logic', 'AND')
                    if logic and logic.upper() == 'OR':
                        salary_mask = salary_filters_mask[0]
                        for m in salary_filters_mask[1:]:
                            salary_mask |= m
                        mask &= salary_mask
                    else:
                        salary_mask = salary_filters_mask[0]
                        for m in salary_filters_mask[1:]:
                            salary_mask &= m
                        mask &= salary_mask
            else:
                if filters.salary.operator and filters.salary.value is not None:
                    if filters.salary.operator == '=':
                        mask &= (self.dataframe['salary'] == filters.salary.value)
                    elif filters.salary.operator == '>':
                        mask &= (self.dataframe['salary'] > filters.salary.value)
                    elif filters.salary.operator == '<':
                        mask &= (self.dataframe['salary'] < filters.salary.value)
                    elif filters.salary.operator == '>=':
                        mask &= (self.dataframe['salary'] >= filters.salary.value)
                    elif filters.salary.operator == '<=':
                        mask &= (self.dataframe['salary'] <= filters.salary.value)
        elif filters.salaryMin is not None:
            mask &= (self.dataframe['salary'] >= filters.salaryMin)
        elif filters.salaryMax is not None:
            mask &= (self.dataframe['salary'] <= filters.salaryMax)
        
        # 日期筛选
        if filters.createTime:
            mask &= (self.dataframe['createTime'] == filters.createTime)
        
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
        elif sort_by:
            print(f"警告: 排序字段 '{sort_by}' 不在DataFrame列中，可用列: {list(filtered_df.columns)}")
        
        # 计算总数
        total_count = len(filtered_df)
        
        # 分页
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_df = filtered_df.iloc[start_index:end_index]
        
        # 将DataFrame转换为字典列表
        data_list = paginated_df.to_dict('records')
        
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
                detail_item = {
                    "label": col_config.label,
                    "value": row_record[prop],
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
        elif 'datetime' in col_type or col == 'createTime':
            column_type = 'date'
            filter_type = 'date'
        elif col == 'id':
            filter_type = 'number'
            fixed = 'left'
        elif col in ['department', 'status']:
            filter_type = 'multi-select'
            # 获取唯一值列表作为选项
            unique_values = df[col].unique().tolist()
            if len(unique_values) <= 100:  # 如果唯一值少于100个，提供下拉选项
                options = [str(v) for v in unique_values]
            else:
                filter_type = 'text'  # 唯一值太多，改用文本筛选
        elif col in ['name', 'email']:
            filter_type = 'text'
        elif col in ['age', 'salary']:
            column_type = 'number'
            filter_type = 'number'
        
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

