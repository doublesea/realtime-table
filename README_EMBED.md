# NiceGUI 嵌入 Vue 应用方案

## 概述

本方案将已实现的 Vue 3 + Element Plus 前端应用嵌入到 NiceGUI 框架中，充分利用 Vue 的丰富功能和 NiceGUI 的 Python 后端集成能力。

## 架构说明

- **前端**: Vue 3 + Element Plus + TypeScript（完整功能）
- **后端**: FastAPI + Pandas（数据处理）
- **框架**: NiceGUI（作为容器和路由）

## 使用步骤

### 1. 构建 Vue 应用

首先需要将 Vue 应用构建为静态文件：

```bash
npm install
npm run build
```

**注意**：如果遇到 `vue-tsc` 版本兼容性问题，可以：
- 使用 `npm run build`（不进行类型检查，推荐用于生产构建）
- 或使用 `npm run build:check`（包含类型检查）

构建完成后，会在 `dist` 目录下生成静态文件。

### 2. 运行 NiceGUI 应用

```bash
python nicegui_vue_embed.py
```

或者使用 uvicorn 运行：

```bash
uvicorn nicegui_vue_embed:app --reload
```

### 3. 访问应用

打开浏览器访问：`http://localhost:8080/data-table`

## 技术实现

### Vue 应用构建配置

- `vite.config.ts` 中设置了 `base: '/static/'`，确保资源路径正确
- 构建后的文件放在 `dist` 目录

### NiceGUI 嵌入方式

使用 `iframe` 方式嵌入 Vue 应用，这样可以：
- 完全隔离 Vue 应用的运行环境
- 避免样式和脚本冲突
- 保持 Vue 应用的独立性

### API 通信

- Vue 应用通过 `/api` 路径访问后端 FastAPI 接口
- FastAPI 后端已配置 CORS，允许所有来源访问
- API 路径在 `src/api/data.ts` 中动态配置

## 文件说明

- `nicegui_vue_embed.py`: NiceGUI 主应用，包含路由和页面定义
- `vite.config.ts`: Vite 构建配置，设置静态资源路径
- `src/api/data.ts`: API 客户端，支持动态 baseURL
- `dist/`: Vue 应用构建输出目录（需要运行 `npm run build` 生成）

## 优势

1. **功能完整**: 保留所有 Vue 前端功能，无需重写
2. **易于维护**: Vue 代码独立，可以继续使用 Vue 开发工具
3. **性能优秀**: Vue 应用经过优化，性能良好
4. **集成简单**: NiceGUI 仅作为容器，集成成本低

## 注意事项

1. 每次修改 Vue 代码后，需要重新运行 `npm run build`
2. 确保 `dist` 目录存在且包含构建后的文件
3. 后端 API 需要运行在可访问的地址（默认 localhost:3001 或通过 NiceGUI 集成）

## 开发模式

如果需要开发调试 Vue 应用：

1. 在一个终端运行 Vue 开发服务器：
   ```bash
   npm run dev
   ```

2. 在另一个终端运行后端 API：
   ```bash
   cd backend
   python main.py
   ```

3. 直接访问 `http://localhost:3000` 进行开发

## 生产部署

1. 构建 Vue 应用：`npm run build`
2. 运行 NiceGUI 应用：`python nicegui_vue_embed.py`
3. 所有功能集成在一个应用中

