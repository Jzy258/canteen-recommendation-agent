# docker — 部署配置

**所有者：C（B 协助 ollama 服务）**

- `docker-compose.yml`：frontend + backend + ollama + mcp-weather 四服务编排
- `Dockerfile.backend`：FastAPI 后端（B 协助，含 ollama 依赖）
- `Dockerfile.frontend`：前端多阶段构建（node → nginx 托管 dist/）
- `nginx.conf`：SPA 路由回退 + `/api` 反向代理到 backend:8000（SSE 关闭缓冲）
- 部署说明见 `docs/DEPLOY.md`；ollama 挂载模型卷避免重复下载

```bash
docker compose -f docker/docker-compose.yml up -d --build
# 前端 http://localhost:8080 · 后端 http://localhost:8000/docs
```
