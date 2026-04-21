# 工厂新媒体代理部署说明（二级目录 zs2sbgl）

通过 `https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/` 在新媒体中访问本项目时，需完成以下代码修改与服务器配置。

## 一、修改过的文件清单（需上传到服务器）

将以下文件按相同路径覆盖到工厂服务器项目目录中：

| 序号 | 文件路径 |
|------|----------|
| 1 | `nginx/nginx.conf` |
| 2 | `docker-compose.yml` |
| 3 | `.env.example` |
| 4 | `frontend/src/utils/request.ts` |
| 5 | `frontend/src/utils/uploadRequest.ts` |
| 6 | `frontend/src/composables/useSparePartDataChanged.ts` |
| 7 | `frontend/src/composables/useMechanicalSparePartDataChanged.ts` |
| 8 | `docs/工厂新媒体代理部署-zs2sbgl.md`（本说明，可选） |
| 9 | `nginx/ssl.conf.example`（可选，仅当需要启用本机 HTTPS 时参考） |

### 领用 500 优化相关（需一并同步）

| 序号 | 文件路径 |
|------|----------|
| 10 | `frontend/src/api/sparePart.ts` |
| 11 | `frontend/src/api/mechanicalSparePart.ts` |
| 12 | `backend/api/app/main.py` |
| 13 | `backend/api/app/api/v1/spare_parts.py` |
| 14 | `backend/api/app/api/v1/mechanical_spare_parts.py` |
| 15 | `backend/api/app/crud/requisition.py` |
| 16 | `backend/api/app/crud/mechanical_requisition.py` |

**推荐同时更新模型（否则领用记录里不会保存“领用原因/使用地点”）：**

| 序号 | 文件路径 |
|------|----------|
| 17 | `backend/api/app/models/requisition_log.py` |
| 18 | `backend/api/app/models/mechanical_requisition_log.py` |

**说明**：仅上传上述修改过的文件即可，无需上传整个仓库。**Nginx 主配置已去掉 HTTPS 块**，无 SSL 证书时也可正常启动（避免 `cannot load certificate` 导致容器退出）。领用接口 500 时，后端会返回具体错误信息与请求ID，便于在服务器日志中按 `request_id` 排查；前端请求体已做兼容，仅传有值字段。crud 已兼容“未更新模型”的旧部署（只传模型上存在的列），若先只更新 crud 不更新模型，领用可成功但不会写入领用原因/使用地点；更新模型并重启后即可完整写入。

### 领用员库存管理页面权限（需一并同步前端）

| 序号 | 文件路径 |
|------|----------|
| 19 | `frontend/src/router/index.ts` |
| 20 | `frontend/src/views/layouts/ElectricalLayout.vue` |
| 21 | `frontend/src/views/layouts/MechanicalLayout.vue` |
| 22 | `frontend/src/App.vue` |

**说明**：电气领用员、机械领用员可访问各自系统的「库存管理」页面（仅前端路由与菜单，后端库存接口已按物资范围放行）。同步后需重新打包前端并更新 `frontend/dist`。

---

## 二、外网访问（工厂代理）：用静态 dist，服务器无需 npm

工厂服务器**无外网**时无法在服务器上执行 `npm install` / `npm run build`。且工厂 Nginx **只代理 `/zs2sbgl/`**，不会转发 `/@vite/client`、`/src/` 等开发路径，因此外网必须用**打包好的静态前端**。

当前逻辑（已写入 nginx 与 docker-compose）：

- Nginx 优先从挂载的 **`frontend/dist`** 提供静态文件（`GET /` → `index.html`，`GET /assets/xxx` → JS/CSS）。
- 若 **`frontend/dist` 为空或未部署**，则回退到 **frontend-dev**（Vite 开发服），内网 `http://172.24.69.125:8080` 照常可用。

### 1. 在能联网的机器上打包（一次性或发版时）

在**有外网**的开发机或构建机上，进入前端目录并打包（不改代码，仅环境变量影响构建结果）：

**Linux / macOS / Git Bash：**
```bash
cd spare_part_system/frontend
npm install
VITE_BASE_PATH=/zs2sbgl/ npm run build
```

**Windows PowerShell：**
```powershell
cd D:\spare_part_system\frontend   # 改为你的项目路径
npm install
$env:VITE_BASE_PATH="/zs2sbgl/"
npm run build
```

完成后会生成 **`frontend/dist`** 目录（内含 `index.html`、`assets/` 等）。

### 2. 把 dist 拷到工厂服务器

将 **`frontend/dist` 目录下的全部内容**上传到工厂服务器上的 **`spare_part_system/frontend/dist/`**（与 docker-compose 中挂载路径一致），例如：

- 用 U 盘/内网共享：把本机 `frontend/dist` 整个目录拷贝到服务器 `spare_part_system/frontend/dist`；
- 或用 scp/rsync（若服务器可被内网另一台机器访问）：
  ```bash
  scp -r frontend/dist root@172.24.69.125:/path/to/spare_part_system/frontend/
  ```

**注意**：服务器上需存在 `frontend/dist` 目录；若不存在，先 `mkdir -p frontend/dist`，再拷贝内容进去（保证 `frontend/dist/index.html`、`frontend/dist/assets/` 等存在）。

### 3. 重启 Nginx

在工厂服务器项目根目录执行：

```bash
docker compose restart nginx
```

之后访问 **https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/** 会走静态 dist，不再依赖 `/@vite/client`。**frontend-dev 仍保留**：未部署 dist 或内网直连 8080 时，会回退到 Vite 开发服，可用性不变。

---

## 三、服务器上需要做的配置（除文件更新外）

### 1. 环境变量（必做）

在项目**根目录**的 `.env` 中配置或确认以下项（若已有则核对一致）：

```ini
# 外网用静态 dist 时，打包时已写死 /zs2sbgl/，此处仅影响 frontend-dev 回退
# VITE_BASE_PATH=/zs2sbgl/

# SSO 单点登录（新媒体登录必配）
SSO_ENABLED=true
SSO_CLIENT_ID=zs2sbgl
SSO_CLIENT_SECRET=uPVGFv6xD5a2JTeguEavUbvL9xLCyNY
SSO_BASE_URL=https://yxcf-yzyy.ynzy-tobacco.com/
SSO_REALM=yxcf
# 回调地址必须与信息科登记的一致，且为代理后的外网地址
SSO_REDIRECT_URI=https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/sso/callback
```

**重要**：`SSO_REDIRECT_URI` 必须与在信息管理科登记的 **redirect_uri** 完全一致（含协议、域名、路径）。登记时需对链接做 urlencode。

### 2. 重启服务（必做）

上传并修改完文件、保存 `.env` 后，在服务器项目根目录执行：

```bash
docker compose restart nginx
# 若尚未部署 dist，内网仍用 frontend-dev，可保持 frontend-dev 运行
# docker compose up -d frontend-dev
```

若希望整栈重启：

```bash
docker compose down && docker compose up -d
```

### 3. 领用 500 排查与数据库表结构

领用接口若仍返回 500，请：

1. **看页面提示**：错误信息中会带「请求ID: req_xxx」，与后端日志对应。
2. **查后端日志**：在服务器上执行 `docker compose logs -f backend`，再操作一次领用，日志中会打印 `领用接口异常 request_id=req_xxx part_id=...` 及具体异常（如数据库列不存在）。
3. **表结构**：若工厂库是早期创建的，`requisition_logs` 可能缺少 `requisition_reason`、`usage_location` 等列。后端启动时会自动检测并执行 ALTER TABLE 添加缺失列；若未生效，可手动执行与 `backend/api/app/main.py` 中一致的 `ALTER TABLE requisition_logs ADD COLUMN ...` 语句，或重新部署最新 backend 并重启一次后端服务。

### 3. 与信息科确认（若尚未登记）

- 在单点登录侧登记的 **redirect_uri** 为：  
  `https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/sso/callback`
- 工厂 Nginx 代理配置为（由信息科或运维配置）：  
  `location /zs2sbgl/ { proxy_pass http://172.24.69.125:8080/; }`  
  即通过 `https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/` 访问本项目。

### 4. 工厂 Nginx 必须支持 WebSocket（多端实时同步必做）

若出现 **WebSocket connection to 'wss://.../zs2sbgl/api/v1/ws/spare-part-events' failed: 404**，说明工厂侧 Nginx 未正确转发 WebSocket 握手（缺少 `Upgrade`、`Connection` 头），后端会按普通 GET 处理并返回 404，多端实时同步会失效。

请让信息科/运维在 **工厂 Nginx** 的 `location /zs2sbgl/` 中增加以下三行（与现有 `proxy_pass` 一起使用）：

```nginx
location /zs2sbgl/ {
    proxy_pass http://172.24.69.125:8080/;   # 保持原有
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

修改后重载工厂 Nginx（如 `nginx -s reload`），再访问页面，WebSocket 应能握手成功，多端数据会实时同步。

---

## 四、访问方式说明

| 访问方式 | 地址 |
|----------|------|
| 新媒体 / 外网 | https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/ |
| 内网直连（可选） | http://172.24.69.125:8080/zs2sbgl/ |

内网直连时也需带 `/zs2sbgl/` 前缀，因为前端已按该 base 构建。

---

## 五、代码改动摘要

- **Nginx**：`location /` 优先用挂载的 `frontend/dist`（`try_files /zs2sbgl$uri ...`），无静态文件时回退到 `@frontend_dev`（Vite 开发服）；工厂代理只转发 `/zs2sbgl/` 得到 `GET /`、`GET /assets/xxx`，均由静态或回退正确响应。
- **Docker**：nginx 增加 volume `./frontend/dist:/usr/share/nginx/html/zs2sbgl`，服务器无需 npm。
- **前端**：打包时使用 `VITE_BASE_PATH=/zs2sbgl/`，请求与 WebSocket 的 base 已用 `config.api.baseURL`（即 `/zs2sbgl/api/v1`）。
- **后端**：通过 `.env` 中的 `SSO_REDIRECT_URI` 使用代理后的外网回调地址，与单点登录登记一致。

完成「二、外网访问」中打包 + 上传 dist + 重启 nginx 后，即可在新媒体中通过 https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/ 访问并正常使用 SSO 登录；未部署 dist 时内网仍可用 frontend-dev。

---

## 六、502 Bad Gateway 排查（访问 /zs2sbgl/sso/callback 报 502 时）

502 表示上游（本机 Nginx 或前端容器）未正常响应，按下面顺序排查。

### 1. 确认环境变量并强制重建前端容器

`.env` 中必须有 `VITE_BASE_PATH=/zs2sbgl/`，且需**重建**前端容器后才会生效（重启可能仍用旧环境）：

```bash
# 在项目根目录
docker compose up -d frontend-dev --force-recreate
docker compose restart nginx
```

### 2. 确认前端容器在跑且无报错

```bash
docker compose ps
docker compose logs frontend-dev --tail 80
```

若 `frontend-dev` 未运行或日志里 Vite 报错，先修好再测。

### 3. 在本机模拟工厂代理请求

工厂代理会把 `https://.../zs2sbgl/sso/callback` 转成对 8080 的 `GET /sso/callback`，在服务器上执行：

```bash
# 应返回 200 和 HTML（或至少非 502）
curl -I "http://127.0.0.1:8080/sso/callback"
```

- 若这里就 502：问题在本机 Nginx 或前端容器，继续看步骤 4、5。  
- 若这里 200：多半是工厂 Nginx 到 172.24.69.125:8080 的网络/防火墙问题，需在工厂侧排查。

### 4. 看本机 Nginx 错误日志

```bash
docker compose exec nginx cat /var/log/nginx/error.log | tail -30
```

关注是否有 `upstream timed out`、`connect() failed` 等，可判断是连不上前端还是超时。

### 5. 从 Nginx 容器内直连前端

```bash
docker compose exec nginx wget -q -O - http://frontend-dev:5173/zs2sbgl/sso/callback | head -5
```

- 若超时或连接失败：前端容器未监听 5173 或网络不通。  
- 若返回 HTML：说明前端正常，502 更可能是 Nginx 配置或工厂代理问题。

### 6. 核对 Nginx 配置

确认已使用带 `rewrite` 和 `proxy_pass` 的 `nginx/nginx.conf`（见“一、修改过的文件清单”），并已重启 Nginx：

```bash
docker compose exec nginx nginx -t
docker compose restart nginx
```

按上述步骤可定位 502 是出在前端未起、环境未生效、本机 Nginx 还是工厂代理。

---

## 七、Nginx 因缺少 SSL 证书无法启动

若日志出现：`cannot load certificate "/etc/nginx/ssl/server.crt": ... No such file or directory`，说明 Nginx 在加载 443 端口的 HTTPS 配置时找不到证书。

**处理方式**：
1. 主配置 `nginx/nginx.conf` 中已**移除 HTTPS server 块**，无证书时 Nginx 可正常启动。请确认服务器上的 `nginx/nginx.conf` 已是此版本。
2. **若仍有 SSL 报错**：多半是 `nginx/conf.d/` 下存在 `ssl.conf`（从 ssl.conf.example 复制过）。请删除或改名：`mv nginx/conf.d/ssl.conf nginx/conf.d/ssl.conf.bak`，然后 `docker compose restart nginx`。
3. 工厂代理访问使用 HTTP 到 8080 即可，不需要本机 443。

若以后需要在本机直接提供 HTTPS（8443）：
1. 在项目根目录执行：`bash ssl/generate-cert.sh` 生成自签名证书；
2. 复制：`cp nginx/ssl.conf.example nginx/conf.d/ssl.conf`；
3. 重启 nginx 容器。

---

## 八、页面白屏或静态资源全是 972 字节（index.html）

现象：打开 `/zs2sbgl` 或 `/zs2sbgl/` 后，请求 `/@vite/client`、`/src/main.ts` 等返回 200 但 body 只有约 972 字节（实为 index.html），页面白屏或报错。

**原因**：前端容器未使用 `VITE_BASE_PATH=/zs2sbgl/`，Vite 仍按 base `/` 运行，资源路径对不上。

**处理**：
1. 确认项目根目录 `.env` 中有：`VITE_BASE_PATH=/zs2sbgl/`
2. **必须重建前端容器**（restart 不会重新读环境变量）：
   ```bash
   docker compose up -d frontend-dev --force-recreate
   docker compose restart nginx
   ```
3. 再访问 https://yxcf-yzyy.ynzy-tobacco.com/zs2sbgl/ 或 http://172.24.69.125:8080/zs2sbgl/
