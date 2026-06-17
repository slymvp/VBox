# VBox 管理后台

## 项目结构

```
admin/
├── src/
│   ├── views/
│   │   ├── login/       # 登录页面
│   │   ├── dashboard/   # 数据看板
│   │   ├── series/      # 剧集管理
│   │   ├── episodes/    # 分集管理（待完善）
│   │   ├── users/       # 用户管理
│   │   └── crawler/     # 爬虫管理（待完善）
│   ├── layout/          # 布局组件
│   ├── router/          # 路由配置
│   ├── utils/           # 工具函数（API请求）
│   ├── App.vue
│   └── main.ts
├── index.html
├── package.json
├── vite.config.ts
└── tsconfig.json
```

## 开发启动

### 1. 安装依赖
```bash
cd admin
npm install
```

### 2. 启动开发服务
```bash
npm run dev
```
服务会在 http://localhost:3001 启动

### 3. 启动后端服务
在另一个终端中启动后端服务（端口 8000）

## 功能说明

### 登录
- 默认账号：admin / admin123
- 登录后会在 localStorage 中保存 token

### 数据看板
- 显示剧集总数、分集总数、用户总数等统计信息
- 快捷操作入口

### 剧集管理
- 剧集列表查询（按平台、类型筛选）
- 删除剧集（会级联删除分集）
- 新增/编辑功能（可根据需要完善）

### 用户管理
- 用户列表查询
- 用户状态管理（启用/禁用）

## 部署

### 构建生产版本
```bash
npm run build
```
构建产物输出到 `dist/` 目录

### 部署
可以将 `dist/` 目录部署到 Nginx 等静态文件服务器，或者由后端 FastAPI 服务提供静态文件

## 注意事项

1. 前端开发服务器已配置代理，`/admin-api` 请求会被代理到 `http://localhost:8000`
2. 生产环境部署时需要确保 API 地址配置正确
3. 管理后台的登录验证是简单实现，生产环境应该使用更安全的方案（如 JWT）
