# NiceGUI 版本的大数据量表格组件

这是将原 Vue + FastAPI 版本重构为 NiceGUI 版本的实现。

## 功能特性

✅ **所有核心功能已实现：**

1. ✅ **行选中保持**：筛选变更时，选中行保持在当前分页，并自动滚动到可见位置
2. ✅ **列隐藏设置**：支持通过列设置下拉菜单显示/隐藏各列
3. ✅ **行展开详情**：双击行或点击详情按钮查看该行详细信息
4. ✅ **全局筛选**：支持全局筛选，实时显示筛选后的总条数
5. ✅ **多条件筛选**：支持年龄和薪资的多条件组合筛选（AND/OR逻辑）
6. ✅ **文本列表筛选**：文本类型列（部门、状态）唯一值小于100时，自动显示下拉列表筛选

## 文件说明

- `nicegui_table.py`: NiceGUI 版本的表格组件主文件
- `nicegui_example.py`: 使用示例文件，展示如何集成到现有 NiceGUI 应用
- `backend/main.py`: 复用了原有的筛选逻辑函数 `build_pandas_filter`

## 使用方法

### 1. 基本使用

```python
from nicegui import ui
from nicegui_table import DataTablePage
from backend.main import init_data, data_df

# 初始化数据
init_data()

# 创建页面
@ui.page('/data-table')
async def data_table_page():
    table_page = DataTablePage(data_df)
    table_page.create_page()

ui.run(port=8080)
```

### 2. 集成到现有 NiceGUI 应用

```python
from nicegui import ui
from nicegui_table import DataTablePage

# 假设你已经有数据源
your_dataframe = pd.DataFrame(...)  # 你的 DataFrame

@ui.page('/your-table')
async def your_table_page():
    table_page = DataTablePage(your_dataframe)
    table_page.create_page()
```

### 3. 运行示例

```bash
python nicegui_example.py
```

然后访问 `http://localhost:8080`

## 主要特点

1. **直接使用 DataFrame**：无需 RESTful API，直接操作 pandas DataFrame
2. **复用现有逻辑**：复用了 `backend/main.py` 中的 `build_pandas_filter` 函数
3. **完全 Python 实现**：所有逻辑都在 Python 中，无需前端代码
4. **与 NiceGUI 原生集成**：使用 NiceGUI 的 Quasar 组件，界面风格统一

## 与 Vue 版本的对比

| 特性 | Vue 版本 | NiceGUI 版本 |
|------|---------|-------------|
| 前端框架 | Vue 3 + TypeScript | NiceGUI (Quasar) |
| 后端 | FastAPI + RESTful API | 直接使用 DataFrame |
| 代码语言 | TypeScript + Python | 纯 Python |
| 组件库 | Element Plus | Quasar |
| 开发复杂度 | 前后端分离，需要维护两套代码 | 统一 Python 开发 |
| 数据通信 | HTTP API 调用 | 直接内存访问 |

## 注意事项

1. **行展开功能**：目前通过双击行来显示详情对话框。如果需要点击"+"列展开，可能需要使用 NiceGUI 的高级功能或自定义组件。

2. **性能优化**：对于超大数据量（百万级以上），建议：
   - 使用数据库而不是内存 DataFrame
   - 实现虚拟滚动
   - 添加缓存机制

3. **筛选逻辑**：筛选逻辑复用了原有的 `build_pandas_filter` 函数，确保与 Vue 版本的行为一致。

## 依赖要求

```bash
pip install nicegui pandas numpy
```

## 后续优化建议

1. 添加导出功能（Excel/CSV）
2. 添加列排序功能
3. 添加列宽调整功能
4. 优化大数据量性能（虚拟滚动）
5. 添加数据缓存机制

