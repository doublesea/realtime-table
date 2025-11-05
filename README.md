# 大数据量表格系统

一个基于 Python + Vue 3 的大数据量表格展示系统，支持千万级数据展示、全局筛选、行选中保持等功能。

## 技术栈

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Element Plus** - Vue 3 组件库
- **Vite** - 快速的前端构建工具
- **Axios** - HTTP 客户端

### 后端
- **FastAPI** - 现代、快速的 Python Web 框架
- **Pandas** - 数据分析和处理库
- **NumPy** - 数值计算库
- **Pydantic** - 数据验证库

## 功能特性

### 1. 大数据量展示
- ✅ 支持 1000 万条数据预生成和展示
- ✅ 服务端分页，每页 100 条数据（可调整）
- ✅ 虚拟滚动，流畅的滚动体验
- ✅ 显示筛选后的准确总数

### 2. 全局筛选功能
- ✅ **列头筛选**：所有列都支持在列头进行筛选
- ✅ **文本筛选**：姓名、邮箱等文本字段支持模糊匹配
- ✅ **下拉筛选**：部门、状态等字段支持下拉选择
- ✅ **数字筛选**：ID、年龄、薪资支持操作符筛选
  - 支持 `=`, `>`, `<`, `>=`, `<=` 操作符
  - 支持多个条件组合（AND/OR 逻辑）
  - 例如：年龄 > 10 AND < 20，薪资 >= 30000 OR < 20000
- ✅ **日期筛选**：创建时间支持日期筛选
- ✅ **筛选作用于全局**：筛选结果基于全部数据，不是当前页
- ✅ **重置筛选**：一键清除所有筛选条件

### 3. 行展开详情
- ✅ 点击行首的 `+` 号展开显示详细信息
- ✅ 每个字段单独一行显示，清晰易读

### 4. 行选中保持可见
- ✅ **行选中**：点击表格行可选中（蓝色高亮显示）
- ✅ **筛选保持**：筛选条件变更时，自动跳转到包含选中行的页面
- ✅ **自动滚动**：自动滚动到选中行，使其在可视区域中间显示
- ✅ **智能处理**：
  - 如果选中行不在筛选结果中，自动清除选中状态
  - 分页变化时不保持选中行（用户手动切换页面）
  - 每页数量变化时，如果选中了行，会保持选中行可见

## 项目结构

```
bigdata_from_plan/
├── backend/                 # 后端目录
│   ├── main.py             # FastAPI 主文件
│   └── requirements.txt     # Python 依赖
├── src/                     # 前端源码
│   ├── api/                # API 接口
│   │   └── data.ts        # 数据接口
│   ├── components/         # Vue 组件
│   │   └── DataTable.vue  # 数据表格组件
│   ├── types/              # TypeScript 类型定义
│   │   └── index.ts       # 类型定义
│   ├── App.vue            # 根组件
│   └── main.ts            # 入口文件
├── package.json            # 前端依赖配置
├── vite.config.ts         # Vite 配置
├── tsconfig.json          # TypeScript 配置
└── README.md              # 项目说明文档
```

## 安装和运行

### 前置要求
- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 后端设置

1. 进入后端目录：
```bash
cd backend
```

2. 安装 Python 依赖：
```bash
pip install -r requirements.txt
```

3. 启动后端服务：
```bash
python main.py
```

后端服务将在 `http://localhost:3001` 启动。

### 前端设置

1. 安装依赖：
```bash
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

前端应用将在 `http://localhost:5173` 启动。

## 使用说明

### 1. 筛选数据

#### 文本筛选
- 在列头输入框中输入文本，支持模糊匹配
- 例如：在"姓名"列输入"用户"，会筛选出所有姓名包含"用户"的记录

#### 数字筛选
- 选择操作符（=、>、<、>=、<=）
- 输入数值
- 支持添加多个条件：
  - 点击"+ 添加条件"按钮
  - 选择逻辑关系（AND/OR）
  - 例如：年龄 > 10 AND < 20 表示年龄在 10 到 20 之间

#### 下拉筛选
- 在列头的下拉框中选择选项
- 例如：在"部门"列选择"技术部"，会筛选出所有技术部的记录

### 2. 查看详情
- 点击行首的 `+` 号展开该行的详细信息
- 再次点击 `-` 号收起详情

### 3. 选中行
- 点击表格中的任意一行，该行会高亮显示（蓝色背景）
- 修改筛选条件后，系统会自动跳转到包含选中行的页面
- 自动滚动到选中行，使其在可视区域中间显示

### 4. 分页操作
- 使用底部的分页组件切换页面
- 可以调整每页显示的数量（50/100/200/500）
- 显示筛选后的总记录数和当前页信息

## API 接口

### 获取数据列表
```
POST /api/data/list
```

请求参数：
```json
{
  "page": 1,
  "pageSize": 100,
  "filters": {
    "age": {
      "operator": ">",
      "value": 30
    },
    "department": "技术部"
  }
}
```

响应：
```json
{
  "success": true,
  "data": {
    "list": [...],
    "total": 12345,
    "page": 1,
    "pageSize": 100
  }
}
```

### 获取选中行位置
```
POST /api/data/row-position
```

请求参数：
```json
{
  "rowId": 123,
  "filters": {...}
}
```

响应：
```json
{
  "success": true,
  "data": {
    "found": true,
    "position": 456
  }
}
```

### 获取筛选选项
```
GET /api/data/filters
```

响应：
```json
{
  "success": true,
  "data": {
    "departments": ["技术部", "销售部", "市场部", "人事部", "财务部"],
    "statuses": ["在职", "离职", "试用期"]
  }
}
```

## 筛选条件说明

### NumberFilter（数字筛选）
```typescript
{
  operator?: '=' | '>' | '<' | '>=' | '<=',
  value?: number
}
```

### FilterGroup（多条件组合）
```typescript
{
  filters: NumberFilter[],
  logic?: 'AND' | 'OR'
}
```

### FilterParams（完整筛选参数）
```typescript
{
  id?: NumberFilter | FilterGroup,
  name?: string,
  email?: string,
  department?: string,
  status?: string,
  age?: NumberFilter | FilterGroup,
  salary?: NumberFilter | FilterGroup,
  createTime?: string
}
```

## 性能优化

1. **数据预生成**：应用启动时生成 10 万条数据，保存在内存中
2. **Pandas 向量化操作**：使用 pandas 进行高效的数据筛选和分页
3. **服务端分页**：只返回当前页的数据，减少网络传输
4. **虚拟滚动**：Element Plus 表格组件内置虚拟滚动支持

## 开发说明

### 数据生成逻辑
- 使用 ID 作为随机种子，确保相同 ID 生成相同的数据
- 年龄范围：18-68
- 薪资范围：10000-60000
- 部门：技术部、销售部、市场部、人事部、财务部
- 状态：在职、离职、试用期

### 筛选逻辑
- 使用 pandas DataFrame 的布尔索引进行筛选
- 支持复杂的多条件组合（AND/OR）
- 筛选结果基于全部数据，不是当前页

## 注意事项

1. **数据量限制**：当前实现支持 10 万条数据，如需支持更大数据量，建议使用数据库
2. **内存占用**：10 万条数据占用约 20-30MB 内存
3. **筛选性能**：对于复杂筛选条件，pandas 操作仍然很快（< 100ms）

## 未来改进方向

- [ ] 支持服务端排序
- [ ] 支持数据导出（Excel、CSV）
- [ ] 支持列自定义显示
- [ ] 支持数据编辑
- [ ] 支持批量操作
- [ ] 使用数据库替代内存数据（支持更大数据量）

## 许可证

MIT License
