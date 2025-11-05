from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
from datetime import datetime, timedelta
import random
import asyncio
import pandas as pd
import numpy as np

app = FastAPI(title="大数据量表格API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，包括 NiceGUI 页面
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局DataFrame存储数据
data_df: pd.DataFrame = None
TOTAL_RECORDS = 100000

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
    value: Optional[int] = None

class FilterGroup(BaseModel):
    filters: List[NumberFilter]
    logic: Optional[str] = 'AND'  # 'AND' 或 'OR'

class FilterParams(BaseModel):
    id: Optional[Union[NumberFilter, FilterGroup]] = None
    name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[Union[str, List[str]]] = None  # 支持单选或多选
    status: Optional[Union[str, List[str]]] = None  # 支持单选或多选
    age: Optional[Union[NumberFilter, FilterGroup]] = None
    ageMin: Optional[int] = None  # 向后兼容
    ageMax: Optional[int] = None  # 向后兼容
    salary: Optional[Union[NumberFilter, FilterGroup]] = None
    salaryMin: Optional[int] = None  # 向后兼容
    salaryMax: Optional[int] = None  # 向后兼容
    createTime: Optional[str] = None
    
    # Pydantic v2 的模型验证器，用于正确解析 Union 类型
    @field_validator('age', 'salary', 'id', mode='before')
    @classmethod
    def parse_union_type(cls, v):
        """解析 Union[NumberFilter, FilterGroup] 类型"""
        if v is None:
            return None
        if isinstance(v, dict):
            # 如果有 filters 键，说明是 FilterGroup
            if 'filters' in v:
                return FilterGroup(**v)
            # 如果有 operator 或 value，说明是 NumberFilter
            elif 'operator' in v or 'value' in v:
                return NumberFilter(**v)
        # 如果已经是实例，直接返回
        return v

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

# 初始化数据（生成1000万条数据并保存到DataFrame）
def init_data():
    """初始化数据，生成1000万条数据并保存到DataFrame"""
    global data_df
    
    print(f"开始生成 {TOTAL_RECORDS} 条数据...")
    departments = ['技术部', '销售部', '市场部', '人事部', '财务部']
    statuses = ['在职', '离职', '试用期']
    
    data_list = []
    for i in range(TOTAL_RECORDS):
        id = i + 1
        name = f"用户_{str(id).zfill(8)}"
        email = f"user{id}@example.com"
        
        # 使用ID作为随机种子，确保相同ID生成相同的数据
        rng = random.Random(id)
        age = rng.randint(18, 68)
        department = rng.choice(departments)
        salary = rng.randint(10000, 60000)
        status = rng.choice(statuses)
        create_time = (datetime.now() - timedelta(days=rng.randint(0, 365))).strftime('%Y-%m-%d')
        
        data_list.append({
            'id': id,
            'name': name,
            'email': email,
            'age': age,
            'department': department,
            'salary': salary,
            'status': status,
            'createTime': create_time
        })
    
    data_df = pd.DataFrame(data_list)
    print(f"数据生成完成，共 {len(data_df)} 条记录")
    print(f"数据预览:\n{data_df.head()}")
    
    return data_df

# 应用启动时初始化数据
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据"""
    # 在后台线程中初始化数据，避免阻塞
    import threading
    threading.Thread(target=init_data, daemon=True).start()
    # 等待数据初始化完成
    import time
    while data_df is None:
        time.sleep(0.1)

# 将筛选条件转换为pandas查询条件
def build_pandas_filter(df: pd.DataFrame, filters: Optional[FilterParams] = None) -> pd.Series:
    """将筛选条件转换为pandas布尔索引"""
    if not filters:
        return pd.Series([True] * len(df))
    
    # 调试：打印筛选条件
    print(f"[筛选调试] 筛选条件类型: {type(filters)}")
    if hasattr(filters, 'age') and filters.age:
        print(f"[筛选调试] 年龄筛选: {filters.age}, 类型: {type(filters.age)}")
        if isinstance(filters.age, FilterGroup):
            print(f"[筛选调试] 年龄筛选逻辑: {filters.age.logic}, 条件数: {len(filters.age.filters)}")
            for i, f in enumerate(filters.age.filters):
                print(f"[筛选调试]   条件{i+1}: {f.operator} {f.value}")
        elif hasattr(filters.age, 'operator'):
            print(f"[筛选调试] 年龄筛选（单条件）: {filters.age.operator} {filters.age.value}")
    
    # 初始化筛选掩码
    mask = pd.Series([True] * len(df))
    
    # ID筛选
    if filters.id:
        if isinstance(filters.id, FilterGroup):
            id_filters_mask = []
            for id_filter in filters.id.filters:
                if id_filter.operator and id_filter.value is not None:
                    if id_filter.operator == '=':
                        id_filters_mask.append(df['id'] == id_filter.value)
                    elif id_filter.operator == '>':
                        id_filters_mask.append(df['id'] > id_filter.value)
                    elif id_filter.operator == '<':
                        id_filters_mask.append(df['id'] < id_filter.value)
                    elif id_filter.operator == '>=':
                        id_filters_mask.append(df['id'] >= id_filter.value)
                    elif id_filter.operator == '<=':
                        id_filters_mask.append(df['id'] <= id_filter.value)
            
            if id_filters_mask:
                # 获取逻辑关系，默认为 AND
                logic = getattr(filters.id, 'logic', 'AND')
                if logic and logic.upper() == 'OR':
                    # OR逻辑：至少一个条件满足
                    id_mask = id_filters_mask[0]
                    for m in id_filters_mask[1:]:
                        id_mask |= m
                    mask &= id_mask
                else:  # AND 或默认
                    # AND逻辑：所有条件都满足
                    id_mask = id_filters_mask[0]
                    for m in id_filters_mask[1:]:
                        id_mask &= m
                    mask &= id_mask
        else:
            if filters.id.operator and filters.id.value is not None:
                if filters.id.operator == '=':
                    mask &= (df['id'] == filters.id.value)
                elif filters.id.operator == '>':
                    mask &= (df['id'] > filters.id.value)
                elif filters.id.operator == '<':
                    mask &= (df['id'] < filters.id.value)
                elif filters.id.operator == '>=':
                    mask &= (df['id'] >= filters.id.value)
                elif filters.id.operator == '<=':
                    mask &= (df['id'] <= filters.id.value)
    
    # 文本筛选
    if filters.name:
        mask &= df['name'].str.contains(filters.name, case=False, na=False)
    if filters.email:
        mask &= df['email'].str.contains(filters.email, case=False, na=False)
    # 部门筛选（支持单选或多选）
    if filters.department:
        if isinstance(filters.department, list):
            mask &= df['department'].isin(filters.department)
        else:
            mask &= (df['department'] == filters.department)
    # 状态筛选（支持单选或多选）
    if filters.status:
        if isinstance(filters.status, list):
            mask &= df['status'].isin(filters.status)
        else:
            mask &= (df['status'] == filters.status)
    
    # 年龄筛选
    if filters.age:
        if isinstance(filters.age, FilterGroup):
            age_filters_mask = []
            for age_filter in filters.age.filters:
                if age_filter.operator and age_filter.value is not None:
                    if age_filter.operator == '=':
                        age_filters_mask.append(df['age'] == age_filter.value)
                    elif age_filter.operator == '>':
                        age_filters_mask.append(df['age'] > age_filter.value)
                    elif age_filter.operator == '<':
                        age_filters_mask.append(df['age'] < age_filter.value)
                    elif age_filter.operator == '>=':
                        age_filters_mask.append(df['age'] >= age_filter.value)
                    elif age_filter.operator == '<=':
                        age_filters_mask.append(df['age'] <= age_filter.value)
            
            if age_filters_mask:
                # 获取逻辑关系，默认为 AND
                logic = getattr(filters.age, 'logic', 'AND')
                if logic and logic.upper() == 'OR':
                    # OR逻辑：至少一个条件满足
                    age_mask = age_filters_mask[0]
                    for m in age_filters_mask[1:]:
                        age_mask |= m
                    mask &= age_mask
                else:  # AND 或默认
                    # AND逻辑：所有条件都满足
                    age_mask = age_filters_mask[0]
                    for m in age_filters_mask[1:]:
                        age_mask &= m
                    mask &= age_mask
        else:
            if filters.age.operator and filters.age.value is not None:
                if filters.age.operator == '=':
                    mask &= (df['age'] == filters.age.value)
                elif filters.age.operator == '>':
                    mask &= (df['age'] > filters.age.value)
                elif filters.age.operator == '<':
                    mask &= (df['age'] < filters.age.value)
                elif filters.age.operator == '>=':
                    mask &= (df['age'] >= filters.age.value)
                elif filters.age.operator == '<=':
                    mask &= (df['age'] <= filters.age.value)
    elif filters.ageMin is not None:
        mask &= (df['age'] >= filters.ageMin)
    elif filters.ageMax is not None:
        mask &= (df['age'] <= filters.ageMax)
    
    # 薪资筛选
    if filters.salary:
        if isinstance(filters.salary, FilterGroup):
            salary_filters_mask = []
            for salary_filter in filters.salary.filters:
                if salary_filter.operator and salary_filter.value is not None:
                    if salary_filter.operator == '=':
                        salary_filters_mask.append(df['salary'] == salary_filter.value)
                    elif salary_filter.operator == '>':
                        salary_filters_mask.append(df['salary'] > salary_filter.value)
                    elif salary_filter.operator == '<':
                        salary_filters_mask.append(df['salary'] < salary_filter.value)
                    elif salary_filter.operator == '>=':
                        salary_filters_mask.append(df['salary'] >= salary_filter.value)
                    elif salary_filter.operator == '<=':
                        salary_filters_mask.append(df['salary'] <= salary_filter.value)
            
            if salary_filters_mask:
                # 获取逻辑关系，默认为 AND
                logic = getattr(filters.salary, 'logic', 'AND')
                if logic and logic.upper() == 'OR':
                    # OR逻辑：至少一个条件满足
                    salary_mask = salary_filters_mask[0]
                    for m in salary_filters_mask[1:]:
                        salary_mask |= m
                    mask &= salary_mask
                else:  # AND 或默认
                    # AND逻辑：所有条件都满足
                    salary_mask = salary_filters_mask[0]
                    for m in salary_filters_mask[1:]:
                        salary_mask &= m
                    mask &= salary_mask
        else:
            if filters.salary.operator and filters.salary.value is not None:
                if filters.salary.operator == '=':
                    mask &= (df['salary'] == filters.salary.value)
                elif filters.salary.operator == '>':
                    mask &= (df['salary'] > filters.salary.value)
                elif filters.salary.operator == '<':
                    mask &= (df['salary'] < filters.salary.value)
                elif filters.salary.operator == '>=':
                    mask &= (df['salary'] >= filters.salary.value)
                elif filters.salary.operator == '<=':
                    mask &= (df['salary'] <= filters.salary.value)
    elif filters.salaryMin is not None:
        mask &= (df['salary'] >= filters.salaryMin)
    elif filters.salaryMax is not None:
        mask &= (df['salary'] <= filters.salaryMax)
    
    # 日期筛选
    if filters.createTime:
        mask &= (df['createTime'] == filters.createTime)
    
    return mask

# 检查数据是否符合筛选条件（保留用于兼容）
def matches_filter(id: int, name: str, email: str, age: int, department: str, 
                   salary: int, status: str, create_time: str, 
                   filters: Optional[FilterParams] = None) -> bool:
    """检查数据是否符合筛选条件"""
    if not filters:
        return True
    
    # ID筛选（支持操作符）
    if filters.id:
        if isinstance(filters.id, FilterGroup):
            # 多个条件组合
            id_results = []
            for id_filter in filters.id.filters:
                if id_filter.operator and id_filter.value is not None:
                    result = False
                    if id_filter.operator == '=':
                        result = (id == id_filter.value)
                    elif id_filter.operator == '>':
                        result = (id > id_filter.value)
                    elif id_filter.operator == '<':
                        result = (id < id_filter.value)
                    elif id_filter.operator == '>=':
                        result = (id >= id_filter.value)
                    elif id_filter.operator == '<=':
                        result = (id <= id_filter.value)
                    id_results.append(result)
            if filters.id.logic == 'OR':
                if not (any(id_results) if id_results else True):
                    return False
            else:  # AND
                if not (all(id_results) if id_results else True):
                    return False
        else:
            id_match = False
            if filters.id.operator == '=' and filters.id.value is not None:
                id_match = (id == filters.id.value)
            elif filters.id.operator == '>' and filters.id.value is not None:
                id_match = (id > filters.id.value)
            elif filters.id.operator == '<' and filters.id.value is not None:
                id_match = (id < filters.id.value)
            elif filters.id.operator == '>=' and filters.id.value is not None:
                id_match = (id >= filters.id.value)
            elif filters.id.operator == '<=' and filters.id.value is not None:
                id_match = (id <= filters.id.value)
            if not id_match:
                return False
    
    # 文本筛选
    if filters.name and filters.name.lower() not in name.lower():
        return False
    if filters.email and filters.email.lower() not in email.lower():
        return False
    # 部门筛选（支持单选或多选）
    if filters.department:
        if isinstance(filters.department, list):
            if department not in filters.department:
                return False
        else:
            if department != filters.department:
                return False
    # 状态筛选（支持单选或多选）
    if filters.status:
        if isinstance(filters.status, list):
            if status not in filters.status:
                return False
        else:
            if status != filters.status:
                return False
    
    # 年龄筛选（支持操作符和多个条件组合，支持AND/OR逻辑）
    if filters.age:
        if isinstance(filters.age, FilterGroup):
            age_results = []
            for age_filter in filters.age.filters:
                if age_filter.operator and age_filter.value is not None:
                    result = False
                    if age_filter.operator == '=':
                        result = (age == age_filter.value)
                    elif age_filter.operator == '>':
                        result = (age > age_filter.value)
                    elif age_filter.operator == '<':
                        result = (age < age_filter.value)
                    elif age_filter.operator == '>=':
                        result = (age >= age_filter.value)
                    elif age_filter.operator == '<=':
                        result = (age <= age_filter.value)
                    age_results.append(result)
            if filters.age.logic == 'OR':
                if not (any(age_results) if age_results else True):
                    return False
            else:  # AND
                if not (all(age_results) if age_results else True):
                    return False
        else:
            age_match = False
            if filters.age.operator == '=' and filters.age.value is not None:
                age_match = (age == filters.age.value)
            elif filters.age.operator == '>' and filters.age.value is not None:
                age_match = (age > filters.age.value)
            elif filters.age.operator == '<' and filters.age.value is not None:
                age_match = (age < filters.age.value)
            elif filters.age.operator == '>=' and filters.age.value is not None:
                age_match = (age >= filters.age.value)
            elif filters.age.operator == '<=' and filters.age.value is not None:
                age_match = (age <= filters.age.value)
            if not age_match:
                return False
    # 向后兼容：范围筛选
    elif filters.ageMin is not None and age < filters.ageMin:
        return False
    elif filters.ageMax is not None and age > filters.ageMax:
        return False
    
    # 薪资筛选（支持操作符和多个条件组合，支持AND/OR逻辑）
    if filters.salary:
        if isinstance(filters.salary, FilterGroup):
            salary_results = []
            for salary_filter in filters.salary.filters:
                if salary_filter.operator and salary_filter.value is not None:
                    result = False
                    if salary_filter.operator == '=':
                        result = (salary == salary_filter.value)
                    elif salary_filter.operator == '>':
                        result = (salary > salary_filter.value)
                    elif salary_filter.operator == '<':
                        result = (salary < salary_filter.value)
                    elif salary_filter.operator == '>=':
                        result = (salary >= salary_filter.value)
                    elif salary_filter.operator == '<=':
                        result = (salary <= salary_filter.value)
                    salary_results.append(result)
            if filters.salary.logic == 'OR':
                if not (any(salary_results) if salary_results else True):
                    return False
            else:  # AND
                if not (all(salary_results) if salary_results else True):
                    return False
        else:
            salary_match = False
            if filters.salary.operator == '=' and filters.salary.value is not None:
                salary_match = (salary == filters.salary.value)
            elif filters.salary.operator == '>' and filters.salary.value is not None:
                salary_match = (salary > filters.salary.value)
            elif filters.salary.operator == '<' and filters.salary.value is not None:
                salary_match = (salary < filters.salary.value)
            elif filters.salary.operator == '>=' and filters.salary.value is not None:
                salary_match = (salary >= filters.salary.value)
            elif filters.salary.operator == '<=' and filters.salary.value is not None:
                salary_match = (salary <= filters.salary.value)
            if not salary_match:
                return False
    # 向后兼容：范围筛选
    elif filters.salaryMin is not None and salary < filters.salaryMin:
        return False
    elif filters.salaryMax is not None and salary > filters.salaryMax:
        return False
    
    # 日期筛选
    if filters.createTime and create_time != filters.createTime:
        return False
    
    return True

# 使用pandas进行筛选和分页
def get_filtered_data(filters: Optional[FilterParams] = None, 
                     page: int = 1, 
                     page_size: int = 100,
                     sort_by: Optional[str] = None,
                     sort_order: Optional[str] = None):
    """使用pandas筛选数据并返回分页结果
    
    Args:
        filters: 筛选条件
        page: 页码
        page_size: 每页大小
        sort_by: 排序字段
        sort_order: 排序方向 ('ascending' 或 'descending')
    
    Returns:
        (filtered_df, total_count): 筛选后的DataFrame和总记录数
    """
    global data_df
    
    if data_df is None:
        raise ValueError("数据未初始化，请重启服务")
    
    # 构建筛选条件
    mask = build_pandas_filter(data_df, filters)
    filtered_df = data_df[mask].copy()
    
    # 排序
    if sort_by and sort_by in filtered_df.columns:
        ascending = sort_order == 'ascending' if sort_order else True
        print(f"执行排序: 字段={sort_by}, 升序={ascending}")
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending, na_position='last')
        print(f"排序后前5条数据的{sort_by}值: {filtered_df[sort_by].head().tolist()}")
    elif sort_by:
        print(f"警告: 排序字段 '{sort_by}' 不在DataFrame列中，可用列: {list(filtered_df.columns)}")
    
    # 计算总数
    total_count = len(filtered_df)
    
    # 分页
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    paginated_df = filtered_df.iloc[start_index:end_index]
    
    return paginated_df, total_count


@app.get("/")
async def root():
    return {"message": "大数据量表格API服务运行中"}

@app.post("/api/data/list")
async def get_data_list(request: ListRequest):
    """获取数据列表（支持分页和筛选）"""
    try:
        global data_df
        
        if data_df is None:
            raise HTTPException(status_code=500, detail="数据未初始化，请重启服务")
        
        # 打印筛选条件详情
        if request.filters:
            print(f"接收到筛选条件: {request.filters}")
            print(f"筛选条件类型: {type(request.filters)}")
            if hasattr(request.filters, 'age') and request.filters.age:
                print(f"年龄筛选对象: {request.filters.age}")
                print(f"年龄筛选对象类型: {type(request.filters.age)}")
                print(f"是否为FilterGroup: {isinstance(request.filters.age, FilterGroup)}")
                if hasattr(request.filters.age, 'logic'):
                    print(f"年龄筛选逻辑: {request.filters.age.logic}")
                if hasattr(request.filters.age, 'filters'):
                    print(f"年龄筛选条件数: {len(request.filters.age.filters)}")
                    for i, f in enumerate(request.filters.age.filters):
                        print(f"  条件{i+1}: {f}")
        
        # 打印排序参数
        print(f"排序参数 - sortBy: {request.sortBy}, sortOrder: {request.sortOrder}")
        
        # 使用pandas进行筛选和分页
        paginated_df, total = get_filtered_data(
            filters=request.filters,
            page=request.page,
            page_size=request.pageSize,
            sort_by=request.sortBy,
            sort_order=request.sortOrder
        )
        
        print(f"筛选后的总数: {total}, 当前页数据量: {len(paginated_df)}")
        
        # 将DataFrame转换为字典列表
        data_list = paginated_df.to_dict('records')
        
        result = {
            "success": True,
            "data": {
                "list": data_list,
                "total": total,
                "page": request.page,
                "pageSize": request.pageSize
            }
        }
        
        return result
    except Exception as e:
        import traceback
        print(f"错误: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/data/row-position")
async def get_row_position(request: dict):
    """获取选中行在筛选结果中的位置"""
    try:
        global data_df
        
        if data_df is None:
            raise HTTPException(status_code=500, detail="数据未初始化")
        
        row_id = request.get('rowId')
        filters = request.get('filters')
        
        if row_id is None:
            raise HTTPException(status_code=400, detail="缺少rowId参数")
        
        # 构建筛选条件
        filter_params = None
        if filters:
            try:
                filter_params = FilterParams(**filters)
                print(f"行位置查询 - 筛选条件解析成功: {filter_params}")
            except Exception as e:
                print(f"行位置查询 - 筛选条件解析失败: {e}, filters: {filters}")
                import traceback
                traceback.print_exc()
                # 即使解析失败，也尝试使用空筛选条件继续查询
        
        mask = build_pandas_filter(data_df, filter_params)
        filtered_df = data_df[mask].copy()
        
        # 查找选中行的位置
        matching_rows = filtered_df[filtered_df['id'] == row_id]
        if not matching_rows.empty:
            # 获取在筛选结果中的位置（从0开始）
            # filtered_df保留了原始索引，我们需要重置索引以便正确计算位置
            filtered_df_reset = filtered_df.reset_index(drop=True)
            matching_rows_reset = filtered_df_reset[filtered_df_reset['id'] == row_id]
            if not matching_rows_reset.empty:
                position = matching_rows_reset.index[0]
                return {
                    "success": True,
                    "data": {
                        "found": True,
                        "position": int(position)
                    }
                }
        
        return {
            "success": True,
            "data": {
                "found": False,
                "position": -1
            }
        }
    except Exception as e:
        import traceback
        print(f"错误: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/data/row-detail")
async def get_row_detail(request: dict):
    """获取行的详细信息
    接收行数据，生成并返回需要展示的详细信息
    """
    try:
        global data_df
        
        if data_df is None:
            raise HTTPException(status_code=500, detail="数据未初始化")
        
        # 获取行数据
        row_data = request.get('row')
        if not row_data:
            raise HTTPException(status_code=400, detail="缺少row参数")
        
        # 从行数据中提取ID
        row_id = row_data.get('id')
        if row_id is None:
            raise HTTPException(status_code=400, detail="行数据中缺少id字段")
        
        # 在DataFrame中通过ID列查找该行
        matching_rows = data_df[data_df['id'] == row_id]
        if len(matching_rows) == 0:
            raise HTTPException(status_code=404, detail=f"未找到ID为 {row_id} 的记录")
        row_record = matching_rows.iloc[0].to_dict()
        
        # 生成详细信息（可以根据业务需求生成更丰富的信息）
        detail = [{
            "label": "ID",
            "value": row_record.get('id'),
            'detail': 'ID',
            'type': 'text',
            'format': 'int'
        }, {
            "label": "姓名",
            "value": row_record.get('name'),
            'detail': '姓名',
            'type': 'text'
        }, {
            "label": "邮箱",
            "value": row_record.get('email'),
            'detail': '邮箱',
            'type': 'text'
        }]
        
        return {
            "success": True,
            "data": detail
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"获取行详情错误: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/filters")
async def get_filters():
    """获取筛选选项"""
    return {
        "success": True,
        "data": {
            "departments": ['技术部', '销售部', '市场部', '人事部', '财务部'],
            "statuses": ['在职', '离职', '试用期']
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)

