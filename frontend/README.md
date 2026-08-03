# frontend — 食堂推荐 Agent 前端

**所有者：C · 前端、测试与文档**

技术栈：Vite + Vue3 + TypeScript + Element Plus + ECharts + vue-router + axios。

## 本地开发

```bash
npm install        # 安装依赖
npm run dev        # 启动 dev server → http://localhost:5173
npm run test       # 运行 Vitest 单元测试
npm run build      # 类型检查 + 生产构建 → dist/
```

## 环境配置

- `VITE_API_BASE`：后端地址，默认 `http://localhost:8000`（见 `.env.development`）
- dev 代理：`/api` 前缀会转发到后端（`vite.config.ts`），后端 CORS 全开，直连亦可

## 目录约定

```
src/
├── api/        # axios 客户端与接口封装（/chat、/chat/stream）
├── components/ # 通用组件
├── views/      # 页面（ChatView 聊天界面等）
├── router/     # vue-router 路由
├── types/      # 与后端契约对应的 TS 类型
└── style.css   # 全局样式
```

## 后端对接（契约见 docs/BC-API文档.md）

- `POST /chat`：`{message, session_id?}` → `{reply, session_id}`
- `POST /chat/stream`：SSE（`session` → `delta*` → `done`）
- `GET /health` / `GET /metrics`

## 测试

- API 层：`src/api/chat.test.ts`（chat / SSE 解析）
- 组件层：`src/views/ChatView.test.ts`（空输入、发送、会话持久化、异常兜底、新会话）
- 运行：`npm run test`（Vitest + jsdom）
