# 白码 iframe 混合内容（Mixed Content）排查与解决

## 现象

- **PC 浏览器**：报错  
  `The page at 'https://haodaapp.yxjyc.com/...' was loaded over HTTPS, but requested an insecure frame 'http://172.24.69.125:8080/'. This request has been blocked.`
- **手机预览**：可能能访问（部分浏览器对混合内容限制较松）。

## 原因

- 父页面是 **HTTPS**（`https://haodaapp.yxjyc.com/...`）
- iframe 写的是 **HTTP**（`http://172.24.69.125:8080/`）
- 浏览器规定：HTTPS 页面里不能嵌入 HTTP 的 iframe（混合内容），会被拦截，PC 上更严格。

## 解决思路（二选一）

### 方案一：同域路径代理（推荐，与白码同 HTTPS、不暴露 IP）

把备件系统挂到白码同一域名下，例如：`https://haodaapp.yxjyc.com/spare/`，由白码 Nginx 把 `/spare/` 反向代理到内网 `172.24.69.125:8080`。这样 iframe 也是 HTTPS，不再有混合内容。

#### 1. 在白码 Nginx 上增加路径代理

在**提供 HTTPS 的** `haodaapp.yxjyc.com` 的 `server { }` 里加入（若白码与备件不在同一台机，则代理到 `http://172.24.69.125:8080/`）：

```nginx
location /spare/ {
    proxy_pass http://172.24.69.125:8080/;   # 备件系统在内网的地址
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
    client_max_body_size 10M;
    proxy_buffering off;
    proxy_request_buffering off;
}
```

保存后：`nginx -t && nginx -s reload`

> 若白码与备件系统在同一台机器，可改为 `proxy_pass http://127.0.0.1:8080/;`。配置模板见：`nginx/baima-path-proxy.conf.example`。

#### 2. 备件系统前端使用 base 路径 `/spare/`

在**备件系统所在机器**（如 172.24.69.125）上：

- **Docker 部署（frontend-dev）**  
  在项目根目录 `.env` 中增加或修改：
  ```bash
  VITE_BASE_PATH=/spare/
  ```
  然后重启前端容器并重启 nginx：
  ```bash
  docker compose up -d --build frontend-dev
  docker compose restart nginx
  ```

- **或本地构建后由 Nginx 托管**  
  在 `frontend` 目录执行：
  ```bash
  VITE_BASE_PATH=/spare/ npm run build
  ```
  再用当前 Nginx 托管 `dist`，保证对外访问为 `http://本机:8080/`（白码会把 `/spare/` 代理到该地址）。

#### 3. 白码 iframe 地址改为同域 HTTPS

在白码自定义页的 iframe **URL** 中填写：

```text
https://haodaapp.yxjyc.com/spare/
```

不要再使用 `http://172.24.69.125:8080/`。

---

### 方案二：备件系统单独开 HTTPS（8443），iframe 用 HTTPS 直连

无法改白码 Nginx 时，可在备件系统上启用 HTTPS（端口 8443），iframe 填 `https://172.24.69.125:8443/`。缺点：暴露 IP，且自签名证书需每个用户在浏览器中信任一次。

1. **在备件系统服务器上生成证书并重启 Nginx**  
   ```bash
   cd /opt/spare_part_system   # 按实际路径
   bash ssl/generate-cert.sh
   docker compose restart nginx
   ```
2. **每个用户**先浏览器访问 `https://172.24.69.125:8443/` 并信任证书。
3. **白码 iframe 地址**填：`https://172.24.69.125:8443/`

---

## 小结

| 方案 | iframe 地址 | 是否改白码 Nginx | 是否暴露 IP | 推荐 |
|------|-------------|------------------|-------------|------|
| 方案一 同域代理 | `https://haodaapp.yxjyc.com/spare/` | 需要 | 否 | ✅ 推荐 |
| 方案二 自签名 HTTPS | `https://172.24.69.125:8443/` | 不需要 | 是 | 临时/应急 |

更完整说明见：[白码对接与部署方案.md](白码对接与部署方案.md)。
