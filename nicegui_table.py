"""
NiceGUI 版本的大数据量表格组件
支持所有核心功能：行选中保持、列隐藏、行展开、全局筛选、多条件筛选等
"""
from nicegui import ui
import pandas as pd
from typing import Optional, Dict, Any, List
from backend.main import build_pandas_filter, FilterParams, NumberFilter, FilterGroup
import asyncio


class DataTablePage:
    """大数据量表格页面 - NiceGUI 版本"""
    
    def __init__(self, data_df: pd.DataFrame):
        """
        Args:
            data_df: 包含数据的 pandas DataFrame，列包括：
                id, name, email, age, department, salary, status, createTime
        """
        if data_df is None:
            raise ValueError("data_df 不能为 None，请先初始化数据")
        
        if not isinstance(data_df, pd.DataFrame):
            raise TypeError(f"data_df 必须是 pandas DataFrame，当前类型: {type(data_df)}")
        
        if len(data_df) == 0:
            raise ValueError("data_df 不能为空")
        
        self.data_df = data_df.copy()
        self.filtered_df = data_df.copy()
        self.selected_row_id = None
        self.selected_row_index = None
        
        # 列配置
        self.column_config = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True, 'sortable': True, 'type': 'number'},
            {'name': 'name', 'label': '姓名', 'field': 'name', 'sortable': True, 'type': 'text'},
            {'name': 'email', 'label': '邮箱', 'field': 'email', 'type': 'text'},
            {'name': 'age', 'label': '年龄', 'field': 'age', 'sortable': True, 'type': 'number'},
            {'name': 'department', 'label': '部门', 'field': 'department', 'type': 'text'},
            {'name': 'salary', 'label': '薪资', 'field': 'salary', 'sortable': True, 'type': 'number'},
            {'name': 'status', 'label': '状态', 'field': 'status', 'type': 'text'},
            {'name': 'createTime', 'label': '创建时间', 'field': 'createTime', 'sortable': True, 'type': 'text'},
        ]
        
        # 列显示状态（默认全部显示）
        self.column_visible = {col['name']: True for col in self.column_config}
        
        # 筛选条件
        self.filters = {
            'id': {'operator': None, 'value': None},
            'name': None,
            'email': None,
            'department': None,
            'status': None,
            'age': [],  # 多条件列表
            'ageLogic': 'AND',
            'salary': [],  # 多条件列表
            'salaryLogic': 'AND',
            'createTime': None
        }
        
        # 分页
        self.page_size = 100
        self.current_page = 1
        self.total_count = 0
        
        # UI 组件引用
        self.table = None
        self.page_info = None
        self.filter_containers = {}
        self.age_filter_rows = []
        self.salary_filter_rows = []
        
    def create_page(self):
        """创建页面"""
        with ui.card().classes('w-full'):
            # 工具栏
            with ui.row().classes('w-full justify-between items-center mb-4'):
                # 列设置按钮
                ui.button('列设置', icon='settings', on_click=self.show_column_settings).classes('mr-2')
                
                # 重置按钮
                ui.button('重置所有筛选', icon='refresh', on_click=self.reset_filters)
            
            # 表格工具栏
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('双击行查看详情').classes('text-sm text-gray-500')
                self.detail_btn = ui.button(
                    '查看选中行详情', 
                    icon='info',
                    on_click=self.show_selected_row_details
                ).classes('bg-blue-500').props('disabled')
            
            # 表格
            self.create_table()
            
            # 分页控件
            with ui.row().classes('w-full justify-between items-center mt-4'):
                self.page_info = ui.label('共 0 条').classes('text-sm')
                
                with ui.row().classes('items-center gap-2'):
                    ui.label('每页显示:').classes('text-sm')
                    page_size_select = ui.select(
                        [50, 100, 200, 500], 
                        value=100,
                        on_change=lambda e: self.change_page_size(e.value)
                    )
                    page_size_select.bind_value_to(self, 'page_size')
            
            # 初始化加载数据
            self.apply_filters()
    
    def create_id_filter(self):
        """创建ID筛选"""
        with ui.column():
            ui.label('ID').classes('text-sm font-bold mb-2')
            with ui.row().classes('items-center gap-2'):
                id_op = ui.select(
                    ['=', '>', '<', '>=', '<='], 
                    label='操作符', 
                    with_input=True
                ).classes('w-24')
                id_val = ui.number(label='值', precision=0, min=0).classes('flex-1')
                id_op.bind_value_to(self.filters['id'], 'operator')
                id_val.bind_value_to(self.filters['id'], 'value')
                id_op.on('update:model-value', self.apply_filters)
                id_val.on('update:model-value', self.apply_filters)
    
    def create_name_filter(self):
        """创建姓名筛选"""
        with ui.column():
            ui.label('姓名').classes('text-sm font-bold mb-2')
            name_filter = ui.input('筛选姓名', on_change=self.apply_filters).classes('w-full')
            name_filter.bind_value_to(self.filters, 'name')
    
    def create_email_filter(self):
        """创建邮箱筛选"""
        with ui.column():
            ui.label('邮箱').classes('text-sm font-bold mb-2')
            email_filter = ui.input('筛选邮箱', on_change=self.apply_filters).classes('w-full')
            email_filter.bind_value_to(self.filters, 'email')
    
    def create_age_filter(self):
        """创建年龄筛选（多条件）"""
        with ui.column():
            ui.label('年龄（支持多条件）').classes('text-sm font-bold mb-2')
            age_container = ui.column().classes('w-full')
            self.filter_containers['age'] = age_container
            self.add_age_filter_row()
    
    def create_department_filter(self):
        """创建部门筛选（列表选择）"""
        with ui.column():
            ui.label('部门').classes('text-sm font-bold mb-2')
            dept_unique = sorted(self.data_df['department'].unique().tolist())
            if len(dept_unique) < 100:
                dept_filter = ui.select(
                    dept_unique,
                    label='筛选部门',
                    with_input=True,
                    on_change=self.apply_filters
                ).classes('w-full')
            else:
                dept_filter = ui.input('筛选部门', on_change=self.apply_filters).classes('w-full')
            dept_filter.bind_value_to(self.filters, 'department')
    
    def create_salary_filter(self):
        """创建薪资筛选（多条件）"""
        with ui.column():
            ui.label('薪资（支持多条件）').classes('text-sm font-bold mb-2')
            salary_container = ui.column().classes('w-full')
            self.filter_containers['salary'] = salary_container
            self.add_salary_filter_row()
    
    def create_status_filter(self):
        """创建状态筛选（列表选择）"""
        with ui.column():
            ui.label('状态').classes('text-sm font-bold mb-2')
            status_unique = sorted(self.data_df['status'].unique().tolist())
            if len(status_unique) < 100:
                status_filter = ui.select(
                    status_unique,
                    label='筛选状态',
                    with_input=True,
                    on_change=self.apply_filters
                ).classes('w-full')
            else:
                status_filter = ui.input('筛选状态', on_change=self.apply_filters).classes('w-full')
            status_filter.bind_value_to(self.filters, 'status')
    
    def create_time_filter(self):
        """创建时间筛选"""
        with ui.column():
            ui.label('创建时间').classes('text-sm font-bold mb-2')
            date_filter = ui.input('YYYY-MM-DD', placeholder='YYYY-MM-DD', on_change=self.apply_filters).classes('w-full')
            date_filter.bind_value_to(self.filters, 'createTime')
    
    def add_age_filter_row(self):
        """添加年龄筛选行（兼容方法）"""
        self.add_age_filter_row_column_header()
    
    def add_age_filter_row_column_header(self):
        """添加年龄筛选行（在列标题处）"""
        container = self.filter_containers.get('age')
        if not container:
            return
            
        filter_row = {'ui': None, 'operator': None, 'value': None, 'logic': None}
        
        # 添加第二个及以后的条件
        with container:
            with ui.row().classes('items-center gap-1 mt-1'):
                # 逻辑选择器（AND/OR）
                logic_select = ui.select(
                    ['AND', 'OR'], 
                    value=self.filters['ageLogic']
                ).classes('w-12 text-xs')
                logic_select.on('update:model-value', 
                               lambda e: setattr(self.filters, 'ageLogic', e.args) or self.apply_filters())
                filter_row['logic'] = logic_select
                
                # 操作符和值
                age_op = ui.select(['=', '>', '<', '>=', '<=']).classes('w-16 text-xs')
                age_val = ui.number(label='', precision=0, min=0, max=100, placeholder='值').classes('flex-1 text-xs')
                delete_btn = ui.button(icon='delete', color='red').classes('text-xs px-1 py-0')
                
                filter_row['operator'] = age_op
                filter_row['value'] = age_val
                filter_row['ui'] = container
                
                # 筛选条件变化事件
                age_op.on('update:model-value', self.apply_filters)
                age_val.on('update:model-value', self.apply_filters)
                
                # 删除按钮事件
                def remove_filter():
                    if filter_row in self.age_filter_rows:
                        self.age_filter_rows.remove(filter_row)
                        # 重新创建筛选行以更新UI
                        self.update_filter_row()
                        self.apply_filters()
                
                delete_btn.on('click', remove_filter)
                
                self.age_filter_rows.append(filter_row)
        
        # 更新第一个条件的"+"按钮显示
        self.update_filter_row()
    
    def add_salary_filter_row(self):
        """添加薪资筛选行（在展开区域）"""
        self.add_salary_filter_row_column_header()
    
    def add_salary_filter_row_column_header(self):
        """添加薪资筛选行（在列标题处）"""
        container = self.filter_containers.get('salary')
        if not container:
            return
            
        filter_row = {'ui': None, 'operator': None, 'value': None, 'logic': None}
        
        # 添加第二个及以后的条件
        with container:
            with ui.row().classes('items-center gap-1 mt-1'):
                # 逻辑选择器（AND/OR）
                logic_select = ui.select(
                    ['AND', 'OR'], 
                    value=self.filters['salaryLogic']
                ).classes('w-12 text-xs')
                logic_select.on('update:model-value', 
                               lambda e: setattr(self.filters, 'salaryLogic', e.args) or self.apply_filters())
                filter_row['logic'] = logic_select
                
                # 操作符和值
                salary_op = ui.select(['=', '>', '<', '>=', '<=']).classes('w-16 text-xs')
                salary_val = ui.number(label='', precision=0, min=0, placeholder='值').classes('flex-1 text-xs')
                delete_btn = ui.button(icon='delete', color='red').classes('text-xs px-1 py-0')
                
                filter_row['operator'] = salary_op
                filter_row['value'] = salary_val
                filter_row['ui'] = container
                
                # 筛选条件变化事件
                salary_op.on('update:model-value', self.apply_filters)
                salary_val.on('update:model-value', self.apply_filters)
                
                # 删除按钮事件
                def remove_filter():
                    if filter_row in self.salary_filter_rows:
                        self.salary_filter_rows.remove(filter_row)
                        # 重新创建筛选行以更新UI
                        self.update_filter_row()
                        self.apply_filters()
                
                delete_btn.on('click', remove_filter)
                
                self.salary_filter_rows.append(filter_row)
        
        # 更新第一个条件的"+"按钮显示
        self.update_filter_row()
    
    def show_column_settings(self):
        """显示列设置对话框"""
        with ui.dialog() as dialog, ui.card().classes('w-80 p-4'):
            ui.label('列设置').classes('text-h6 mb-4 font-bold')
            
            with ui.column().classes('gap-2'):
                for col in self.column_config:
                    checkbox = ui.checkbox(
                        col['label'], 
                        value=self.column_visible[col['name']]
                    )
                    def on_checkbox_change(e, col_name=col['name']):
                        # NiceGUI checkbox 事件传递的值可能是直接的值，需要正确提取
                        value = e.args if hasattr(e, 'args') else e
                        # 处理各种可能的类型
                        if isinstance(value, (list, tuple)):
                            visible = bool(value[0]) if len(value) > 0 else False
                        else:
                            visible = bool(value)
                        self.toggle_column(col_name, visible)
                    
                    checkbox.on('update:model-value', on_checkbox_change)
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('关闭', on_click=dialog.close)
        
        dialog.open()
    
    def toggle_column(self, col_name: str, visible: bool):
        """切换列显示/隐藏"""
        # 确保 visible 是布尔值
        visible = bool(visible)
        
        # 计算当前可见列的数量（只计算布尔值）
        visible_count = sum(1 for v in self.column_visible.values() if isinstance(v, bool) and v)
        
        if not visible and visible_count <= 1:
            ui.notify('至少需要显示一列', type='warning')
            return
        
        self.column_visible[col_name] = visible
        self.update_table_columns()
        self.load_table_data()
    
    def update_table_columns(self):
        """更新表格列"""
        visible_columns = [
            {
                'name': col['name'],
                'label': col['label'],
                'field': col['field'],
                'required': col.get('required', False),
                'sortable': col.get('sortable', False),
                'align': 'left'
            }
            for col in self.column_config if self.column_visible.get(col['name'], True)
        ]
        
        if self.table:
            self.table.columns = visible_columns
        
        # 更新筛选行以匹配新的列布局
        self.update_filter_row()
    
    def update_filter_row(self):
        """更新筛选行（当列显示/隐藏或筛选条件变化时）"""
        if hasattr(self, 'filter_row_container'):
            self.filter_row_container.clear()
            with self.filter_row_container:
                # 展开列占位
                ui.column().classes('w-12')
                
                # 为每个可见的列创建筛选控件
                for col in self.column_config:
                    if not self.column_visible.get(col['name'], True):
                        continue
                    
                    with ui.column().classes('flex-1 min-w-32'):
                        ui.label(col['label']).classes('text-xs font-bold mb-1 text-gray-700')
                        self.create_column_filter(col['name'], col['type'])
    
    def create_table(self):
        """创建表格"""
        # 创建筛选行（放在表格上方，模拟列标题筛选）
        self.create_filter_row()
        
        # 根据列可见性过滤列
        visible_columns = [
            {
                'name': col['name'],
                'label': col['label'],
                'field': col['field'],
                'required': col.get('required', False),
                'sortable': col.get('sortable', False),
                'align': 'left'
            }
            for col in self.column_config if self.column_visible.get(col['name'], True)
        ]
        
        # 添加展开/详情列
        visible_columns.insert(0, {
            'name': 'expand',
            'label': '+',
            'field': 'expand',
            'required': False,
            'sortable': False,
            'align': 'center',
            'width': '50px'
        })
        
        self.table = ui.table(
            columns=visible_columns,
            rows=[],
            row_key='id',
            pagination={'rowsPerPage': self.page_size, 'page': 1},
            selection='single'
        ).classes('w-full').style('height: calc(100vh - 450px)')
        
        # 绑定行选择事件
        self.table.on('select', self.on_row_select)
    
    def create_filter_row(self):
        """创建筛选行（模拟列标题筛选）"""
        # 筛选行容器 - 放在表格上方，布局与表格列对齐
        self.filter_row_container = ui.row().classes('w-full gap-2 items-start mb-2 p-2 bg-gray-50 border-b')
        
        with self.filter_row_container:
            # 展开列占位（50px）
            ui.column().classes('w-12')
            
            # 为每个可见的列创建筛选控件
            for col in self.column_config:
                if not self.column_visible.get(col['name'], True):
                    continue
                
                with ui.column().classes('flex-1 min-w-32'):
                    ui.label(col['label']).classes('text-xs font-bold mb-1 text-gray-700')
                    self.create_column_filter(col['name'], col['type'])
    
    def create_column_filter(self, col_name: str, col_type: str):
        """为单个列创建筛选控件"""
        if col_name == 'id':
            # ID 筛选：操作符 + 数值
            with ui.row().classes('items-center gap-1'):
                id_op = ui.select(
                    ['=', '>', '<', '>=', '<='], 
                    with_input=True
                ).classes('w-16 text-xs')
                id_op.bind_value_to(self.filters['id'], 'operator')
                id_op.on('update:model-value', self.apply_filters)
                
                id_val = ui.number(
                    label='', 
                    precision=0, 
                    min=0,
                    placeholder='值'
                ).classes('flex-1 text-xs')
                id_val.bind_value_to(self.filters['id'], 'value')
                id_val.on('update:model-value', self.apply_filters)
        
        elif col_name == 'name':
            # 姓名筛选：文本输入
            name_filter = ui.input(
                placeholder='筛选姓名',
                on_change=self.apply_filters
            ).classes('w-full text-xs')
            name_filter.bind_value_to(self.filters, 'name')
        
        elif col_name == 'email':
            # 邮箱筛选：文本输入
            email_filter = ui.input(
                placeholder='筛选邮箱',
                on_change=self.apply_filters
            ).classes('w-full text-xs')
            email_filter.bind_value_to(self.filters, 'email')
        
        elif col_name == 'age':
            # 年龄筛选：多条件（在列标题处显示）
            age_container = ui.column().classes('gap-1')
            self.filter_containers['age'] = age_container
            
            with age_container:
                # 创建第一个筛选条件
                if len(self.age_filter_rows) == 0:
                    filter_row = {'ui': None, 'operator': None, 'value': None, 'logic': None}
                    
                    with ui.row().classes('items-center gap-1'):
                        age_op = ui.select(['=', '>', '<', '>=', '<=']).classes('w-16 text-xs')
                        age_val = ui.number(label='', precision=0, min=0, max=100, placeholder='值').classes('flex-1 text-xs')
                        add_btn = ui.button('+', on_click=self.add_age_filter_row_column_header).classes('text-xs px-1 py-0')
                        
                        filter_row['operator'] = age_op
                        filter_row['value'] = age_val
                        filter_row['ui'] = age_container
                        
                        # 筛选条件变化事件
                        age_op.on('update:model-value', self.apply_filters)
                        age_val.on('update:model-value', self.apply_filters)
                        
                        self.age_filter_rows.append(filter_row)
                else:
                    # 显示已有的第一个条件
                    age_row = self.age_filter_rows[0]
                    with ui.row().classes('items-center gap-1'):
                        age_op = age_row['operator']
                        age_val = age_row['value']
                        # 添加条件按钮（如果只有一个条件）
                        if len(self.age_filter_rows) == 1:
                            add_btn = ui.button('+', on_click=self.add_age_filter_row_column_header).classes('text-xs px-1 py-0')
        
        elif col_name == 'department':
            # 部门筛选：下拉列表（如果唯一值<100）
            dept_unique = sorted(self.data_df['department'].unique().tolist())
            if len(dept_unique) < 100:
                dept_filter = ui.select(
                    dept_unique,
                    with_input=True,
                    on_change=self.apply_filters
                ).classes('w-full text-xs')
            else:
                dept_filter = ui.input(
                    placeholder='筛选部门',
                    on_change=self.apply_filters
                ).classes('w-full text-xs')
            dept_filter.bind_value_to(self.filters, 'department')
        
        elif col_name == 'salary':
            # 薪资筛选：多条件（在列标题处显示）
            salary_container = ui.column().classes('gap-1')
            self.filter_containers['salary'] = salary_container
            
            with salary_container:
                # 创建第一个筛选条件
                if len(self.salary_filter_rows) == 0:
                    filter_row = {'ui': None, 'operator': None, 'value': None, 'logic': None}
                    
                    with ui.row().classes('items-center gap-1'):
                        salary_op = ui.select(['=', '>', '<', '>=', '<=']).classes('w-16 text-xs')
                        salary_val = ui.number(label='', precision=0, min=0, placeholder='值').classes('flex-1 text-xs')
                        add_btn = ui.button('+', on_click=self.add_salary_filter_row_column_header).classes('text-xs px-1 py-0')
                        
                        filter_row['operator'] = salary_op
                        filter_row['value'] = salary_val
                        filter_row['ui'] = salary_container
                        
                        # 筛选条件变化事件
                        salary_op.on('update:model-value', self.apply_filters)
                        salary_val.on('update:model-value', self.apply_filters)
                        
                        self.salary_filter_rows.append(filter_row)
                else:
                    # 显示已有的第一个条件（从已存在的筛选条件中获取）
                    if len(self.salary_filter_rows) > 0:
                        salary_row = self.salary_filter_rows[0]
                        with ui.row().classes('items-center gap-1'):
                            # 重新创建UI组件以显示当前值
                            salary_op = salary_row['operator']
                            salary_val = salary_row['value']
                            # 添加条件按钮（如果只有一个条件）
                            if len(self.salary_filter_rows) == 1:
                                add_btn = ui.button('+', on_click=self.add_salary_filter_row_column_header).classes('text-xs px-1 py-0')
        
        elif col_name == 'status':
            # 状态筛选：下拉列表（如果唯一值<100）
            status_unique = sorted(self.data_df['status'].unique().tolist())
            if len(status_unique) < 100:
                status_filter = ui.select(
                    status_unique,
                    with_input=True,
                    on_change=self.apply_filters
                ).classes('w-full text-xs')
            else:
                status_filter = ui.input(
                    placeholder='筛选状态',
                    on_change=self.apply_filters
                ).classes('w-full text-xs')
            status_filter.bind_value_to(self.filters, 'status')
        
        elif col_name == 'createTime':
            # 创建时间筛选：日期输入
            date_filter = ui.input(
                placeholder='YYYY-MM-DD',
                on_change=self.apply_filters
            ).classes('w-full text-xs')
            date_filter.bind_value_to(self.filters, 'createTime')
    
    def build_filter_params(self) -> Optional[FilterParams]:
        """构建筛选参数"""
        filters = {}
        
        # ID 筛选
        if self.filters['id']['operator'] and self.filters['id']['value'] is not None:
            filters['id'] = NumberFilter(
                operator=self.filters['id']['operator'],
                value=int(self.filters['id']['value'])
            )
        
        # 文本筛选
        if self.filters['name']:
            filters['name'] = self.filters['name']
        if self.filters['email']:
            filters['email'] = self.filters['email']
        if self.filters['department']:
            filters['department'] = self.filters['department']
        if self.filters['status']:
            filters['status'] = self.filters['status']
        if self.filters['createTime']:
            filters['createTime'] = self.filters['createTime']
        
        # 年龄筛选（多条件）
        age_filters = []
        for filter_row in self.age_filter_rows:
            if filter_row['operator'].value and filter_row['value'].value is not None:
                age_filters.append(NumberFilter(
                    operator=filter_row['operator'].value,
                    value=int(filter_row['value'].value)
                ))
        
        if age_filters:
            if len(age_filters) == 1:
                filters['age'] = age_filters[0]
            else:
                filters['age'] = FilterGroup(
                    filters=age_filters,
                    logic=self.filters['ageLogic']
                )
        
        # 薪资筛选（多条件）
        salary_filters = []
        for filter_row in self.salary_filter_rows:
            if filter_row['operator'].value and filter_row['value'].value is not None:
                salary_filters.append(NumberFilter(
                    operator=filter_row['operator'].value,
                    value=int(filter_row['value'].value)
                ))
        
        if salary_filters:
            if len(salary_filters) == 1:
                filters['salary'] = salary_filters[0]
            else:
                filters['salary'] = FilterGroup(
                    filters=salary_filters,
                    logic=self.filters['salaryLogic']
                )
        
        return FilterParams(**filters) if filters else None
    
    def apply_filters(self):
        """应用筛选条件"""
        # 构建筛选参数
        filter_params = self.build_filter_params()
        
        # 应用筛选
        mask = build_pandas_filter(self.data_df, filter_params)
        self.filtered_df = self.data_df[mask].copy()
        
        # 计算总数
        self.total_count = len(self.filtered_df)
        
        # 如果选中了行，查找它在筛选结果中的位置
        if self.selected_row_id is not None:
            matching_rows = self.filtered_df[self.filtered_df['id'] == self.selected_row_id]
            if not matching_rows.empty:
                # 计算选中行在新筛选结果中的位置
                filtered_reset = self.filtered_df.reset_index(drop=True)
                self.selected_row_index = filtered_reset.index[
                    filtered_reset['id'] == self.selected_row_id
                ].tolist()[0]
                # 计算应该在哪一页
                self.current_page = (self.selected_row_index // self.page_size) + 1
            else:
                # 选中行不在筛选结果中，清除选中状态
                self.selected_row_id = None
                self.selected_row_index = None
                self.current_page = 1
        else:
            # 如果没有选中行，保持在第一页
            self.current_page = 1
        
        # 加载数据
        self.load_table_data()
    
    def load_table_data(self):
        """加载表格数据"""
        # 分页
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        page_data = self.filtered_df.iloc[start_idx:end_idx]
        
        # 转换为字典列表
        rows = page_data.to_dict('records')
        
        # 格式化数据
        for row in rows:
            # 保持原始薪资值，但显示格式化后的值
            original_salary = row['salary']
            row['_salary_original'] = original_salary  # 保存原始值
            row['salary'] = f"¥{original_salary:,}"  # 显示格式化后的值
            # 添加展开按钮数据
            row['expand'] = '+'  # 展开符号
        
        # 更新表格
        self.table.rows = rows
        # NiceGUI 表格的分页可能需要通过 props 设置，或者直接赋值
        try:
            # 尝试直接设置 pagination 属性
            if hasattr(self.table, 'pagination'):
                self.table.pagination = {
                    'rowsPerPage': self.page_size,
                    'page': self.current_page,
                    'rowsNumber': self.total_count
                }
        except:
            # 如果直接设置失败，尝试其他方式
            pass
        
        # 更新分页信息
        self.page_info.text = f'共 {self.total_count:,} 条'
        
        # 如果选中行在当前页，保持选中状态并滚动到该行
        if self.selected_row_id:
            for i, row in enumerate(rows):
                if row['id'] == self.selected_row_id:
                    self.table.selected = [row]
                    # 滚动到选中行
                    ui.timer(0.1, lambda: self.scroll_to_row(i), once=True)
                    break
    
    def scroll_to_row(self, row_index: int):
        """滚动到指定行"""
        ui.run_javascript(f'''
            setTimeout(() => {{
                const table = document.querySelector('.q-table');
                if (table) {{
                    const rows = table.querySelectorAll('tbody tr');
                    if (rows[{row_index}]) {{
                        rows[{row_index}].scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                }}
            }}, 100);
        ''')
    
    def on_table_request(self, e):
        """处理表格请求（分页、排序等）"""
        # NiceGUI 表格可能通过不同方式触发分页
        # 这里我们通过监听表格的 pagination 属性变化来处理
        if hasattr(e, 'args') and e.args:
            if 'pagination' in e.args:
                pagination = e.args['pagination']
                self.current_page = pagination.get('page', 1)
                self.page_size = pagination.get('rowsPerPage', self.page_size)
                self.load_table_data()
    
    def on_row_select(self, e):
        """处理行选择"""
        # NiceGUI 表格的选择事件格式可能不同
        selection = None
        if hasattr(e, 'args'):
            selection = e.args
        elif hasattr(e, 'selection'):
            selection = e.selection
        elif isinstance(e, (list, tuple)) and len(e) > 0:
            selection = e[0] if isinstance(e[0], dict) else e
        
        if selection:
            if isinstance(selection, dict) and 'id' in selection:
                self.selected_row_id = selection['id']
            elif isinstance(selection, list) and len(selection) > 0:
                if isinstance(selection[0], dict) and 'id' in selection[0]:
                    self.selected_row_id = selection[0]['id']
            
            if self.selected_row_id:
                # 计算选中行在筛选结果中的位置
                matching_rows = self.filtered_df[self.filtered_df['id'] == self.selected_row_id]
                if not matching_rows.empty:
                    filtered_reset = self.filtered_df.reset_index(drop=True)
                    self.selected_row_index = filtered_reset.index[
                        filtered_reset['id'] == self.selected_row_id
                    ].tolist()[0]
                
                # 启用详情按钮
                if hasattr(self, 'detail_btn'):
                    self.detail_btn.props(remove='disabled')
                ui.notify(f'已选中行 ID: {self.selected_row_id}', type='info', timeout=1500)
    
    def show_selected_row_details(self):
        """显示选中行的详情"""
        if self.selected_row_id:
            # 从当前页数据中查找
            current_rows = self.table.rows
            for row in current_rows:
                if row['id'] == self.selected_row_id:
                    self.show_row_details(row)
                    return
            # 如果不在当前页，从 DataFrame 中获取
            matching_row = self.data_df[self.data_df['id'] == self.selected_row_id]
            if not matching_row.empty:
                row_dict = matching_row.iloc[0].to_dict()
                self.show_row_details(row_dict)
    
    def show_row_details(self, row: dict):
        """显示行详情（展开功能）"""
        # 获取原始行数据（从 DataFrame 中获取）
        row_id = row['id']
        original_row = self.data_df[self.data_df['id'] == row_id].iloc[0]
        
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-2xl p-6'):
            ui.label('行详情').classes('text-h6 mb-4 font-bold')
            
            details = [
                ('ID', original_row['id']),
                ('姓名', original_row['name']),
                ('邮箱', original_row['email']),
                ('年龄', f"{original_row['age']} 岁"),
                ('部门', original_row['department']),
                ('薪资', f"¥{original_row['salary']:,}"),
                ('状态', original_row['status']),
                ('创建时间', original_row['createTime']),
            ]
            
            for label, value in details:
                with ui.row().classes('w-full items-center mb-3 p-2 hover:bg-gray-100 rounded'):
                    ui.label(label).classes('font-bold min-w-24 text-gray-600')
                    ui.label(str(value)).classes('flex-1 text-gray-800')
            
            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('关闭', on_click=dialog.close, icon='close').classes('bg-gray-500')
        
        dialog.open()
    
    def change_page_size(self, size: int):
        """改变每页显示数量"""
        self.page_size = size
        if self.selected_row_id:
            # 重新计算选中行应该在哪一页
            matching_rows = self.filtered_df[self.filtered_df['id'] == self.selected_row_id]
            if not matching_rows.empty:
                filtered_reset = self.filtered_df.reset_index(drop=True)
                self.selected_row_index = filtered_reset.index[
                    filtered_reset['id'] == self.selected_row_id
                ].tolist()[0]
                self.current_page = (self.selected_row_index // self.page_size) + 1
        else:
            self.current_page = 1
        # 重新加载数据
        self.load_table_data()
        # 更新表格的分页设置
        if self.table:
            try:
                # 尝试更新表格的分页属性
                if hasattr(self.table, 'props'):
                    self.table.props(f':pagination="{{ rowsPerPage: {self.page_size}, page: {self.current_page}, rowsNumber: {self.total_count} }}"')
            except:
                pass
    
    def reset_filters(self):
        """重置所有筛选"""
        self.filters = {
            'id': {'operator': None, 'value': None},
            'name': None,
            'email': None,
            'department': None,
            'status': None,
            'age': [],
            'ageLogic': 'AND',
            'salary': [],
            'salaryLogic': 'AND',
            'createTime': None
        }
        self.age_filter_rows = []
        self.salary_filter_rows = []
        self.selected_row_id = None
        self.selected_row_index = None
        # 禁用详情按钮
        if hasattr(self, 'detail_btn'):
            self.detail_btn.props('disabled')
        # 重新创建筛选UI
        self.filter_containers['age'].clear()
        self.filter_containers['salary'].clear()
        self.add_age_filter_row()
        self.add_salary_filter_row()
        self.apply_filters()
