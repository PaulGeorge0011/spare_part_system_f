# 备件管理系统 — CentOS 7 云服务器部署指南

本文档面向 **CentOS 7** 云服务器，完成备件管理系统的 **Docker 独立部署**。通用步骤（环境变量、HTTPS 等）可配合 [云服务器部署指南.md](云服务器部署指南.md) 使用。

---

## 部署场景说明

- **云服务器**：已通过 Docker 部署 **白码低代码平台**（白码已占用 **80** 端口），Docker 20.10.16、**Docker Compose 1.29.1** 已安装。**工厂服务器无法连接外网**，不能从 Docker Hub 拉取镜像。
- **本项目**：与白码同机独立部署，通过 **docker-compose** 编排；**端口**使用项目当前配置（Nginx 对外 **8080/8443**）；**所有密码维持项目当前设置，不做变动**。
- **访问方式**：用户从白码 **自定义页面** 的链接或 iframe 跳转到本系统，访问地址为 **`http://服务器IP:8080`**（见 [白码对接与部署方案.md](白码对接与部署方案.md)）。
- **文档约定**：工厂**无外网**时需按 **「四、离线镜像准备」** 在有外网机器上导出镜像，再在服务器上加载后启动；有外网时可直接从 **「六、上传项目代码」** 开始。

---

## 一、部署前准备

### 1.1 服务器要求

| 项目     | 建议配置                          |
|----------|-----------------------------------|
| 系统     | CentOS 7.x（64 位）               |
| Docker   | 已安装 20.10.16                   |
| Docker Compose | 已安装 1.29.1（命令：`docker-compose`） |
| CPU/内存 | 至少 2 核 4 GB（与白码同机时建议适当加大） |
| 磁盘     | 至少 40 GB                        |
| 网络     | 公网 IP；端口见下方说明           |

### 1.2 本项目端口与默认配置一览

白码已占用 **80** 端口，本项目 **Nginx 已配置为对外 8080/8443**，其余端口与项目当前一致且未被占用，**直接使用当前配置部署**。密码维持项目默认，不做变动。

| 服务        | 主机端口 | 说明 |
|-------------|----------|------|
| Nginx（Web）| **8080**、**8443** | 因 80 被白码占用，对外访问用 `http://IP:8080` 或 `https://IP:8443` |
| MySQL       | 3307     | 容器内 3306 |
| Redis       | 6379     | |
| MinIO API   | 9000     | MinIO 控制台 9001 |
| FastAPI     | 8888     | 容器内 8000，由 Nginx 反向代理，一般不直连 |
| Frontend    | 3000     | 容器内 80，由 Nginx 反向代理 |
| Django Admin| 8001     | 可选管理后台 |

**默认密码（本方案维持不变）**：

| 用途       | 默认账号/变量 | 默认值 |
|------------|----------------|--------|
| 系统管理员 | admin / admin123 | 登录后可在用户管理中修改 |
| MySQL root | MYSQL_ROOT_PASSWORD | 06002336fwbSQL |
| MySQL 应用 | MYSQL_USER / MYSQL_PASSWORD | sparepart / sparepart123 |
| MinIO      | MINIO_ROOT_USER / MINIO_ROOT_PASSWORD | admin / 06002336fwbMINIO |
| JWT        | SECRET_KEY | dev-secret-key-change-in-production（来自 compose 默认） |

### 1.3 登录服务器

使用 SSH 登录（将 `root` 和 IP 替换为你的账号与公网 IP）：

```bash
ssh root@你的服务器公网IP
```

---

## 二、确认 Docker Compose 1.29.1

当前环境已安装 **Docker Compose 1.29.1**，使用命令 **`docker-compose`**（带连字符）。部署前建议确认版本：

```bash
docker-compose --version
```

应看到类似：`docker-compose version 1.29.1, build ...`。本文档后续所有编排命令均使用 **`docker-compose`**，与 1.29.1 一致。当前项目 `docker-compose.yml` 与 1.29.1 兼容，可直接使用。

**若其他环境未安装 Compose**：可参考 [云服务器部署指南.md](云服务器部署指南.md) 中的安装说明，或使用项目内 **`scripts/run-without-compose.sh`** 通过纯 `docker run` 启动（见该脚本内注释）。

---

## 三、CentOS 7 系统准备（可选）

从零安装 Docker 或需做系统加固时执行本节；若仅需安装 Docker Compose，可跳过。

### 3.1 更新系统并安装基础工具

```bash
# 更新系统
yum update -y

# 安装常用工具（Git、curl、vim 等）
yum install -y curl git vim
```

### 3.2 关闭 SELinux（可选，建议先关闭以便 Docker 正常运行）

若启用 SELinux 可能导致容器内挂载或网络异常，部署阶段可先关闭：

```bash
# 查看当前状态
getenforce

# 临时关闭（重启后恢复）
setenforce 0

# 永久关闭：编辑 /etc/selinux/config，将 SELINUX=enforcing 改为 SELINUX=disabled
sed -i 's/^SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
```

**注意**：若需保留 SELinux，请自行配置策略以放行 Docker 与 Nginx。

### 3.3 配置防火墙（firewalld）

CentOS 7 默认使用 firewalld，需放行 HTTP/HTTPS：

```bash
# 查看状态
firewall-cmd --state

# 本系统 Web 使用 8080/8443（80 已被白码占用）
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --permanent --add-port=8443/tcp

# 重载使生效
firewall-cmd --reload

# 确认
firewall-cmd --list-all
```

若使用云厂商安全组，请在控制台放行 **8080**、**8443**（以及 SSH 的 22）。本方案不占用 80/443。

---

## 四、离线镜像准备（工厂无外网时必做）

工厂服务器**无法连接外网**，`docker-compose up -d` 会因无法拉取镜像而报错。需在**有外网的电脑**上先拉取并导出镜像，再拷贝到工厂服务器加载。

### 4.1 在有外网的电脑上执行

在能上网的电脑上（与工厂服务器架构一致，建议同為 Linux x86_64），进入项目目录：

```bash
cd /path/to/spare_part_system
```

**步骤 1：拉取基础镜像并构建项目镜像**

```bash
# 拉取并构建全部镜像（需联网）
docker-compose pull
docker-compose build
```

**步骤 2：导出镜像为 tar 文件**

可使用项目提供的脚本（推荐）：

```bash
bash scripts/save-images-for-offline.sh
```

或手动执行（镜像名以当前目录为准，一般为 `spare_part_system-xxx`）：

```bash
docker save -o spare_part_images.tar \
  minio/minio:latest \
  minio/mc:latest \
  mysql:8.0 \
  redis:7-alpine \
  nginx:alpine \
  spare_part_system-fastapi:latest \
  spare_part_system-frontend-dev:latest \
  spare_part_system-django-admin:latest
```

若镜像名不同（如目录名不是 `spare_part_system`），可先执行 `docker images` 查看实际名称，再将上述 `spare_part_system-*` 替换为实际名称。

**步骤 3：拷贝到工厂服务器**

将 `spare_part_images.tar` 与项目代码一起，通过 U 盘、内网共享或跳板机拷贝到工厂服务器的 `/opt`（或项目所在目录）。例如：

```bash
scp spare_part_images.tar root@工厂服务器IP:/opt/
```

---

## 五、从零安装 Docker（可选）

仅当服务器**尚未安装 Docker** 时执行本节；若已有 Docker 20.10.16，请从 **「六、上传项目代码」** 开始。**仅限本地源时**：无法使用下文中的在线 yum 源，需使用工厂提供的本地 yum 源（若包含 Docker）或由运维提供 Docker 离线安装包。

### 5.1 安装 Docker CE

```bash
# 安装 yum 工具
yum install -y yum-utils

# 添加 Docker 官方仓库（CentOS 7）
yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 若上面地址较慢，可使用国内镜像（阿里云示例）
# yum-config-manager --add-repo https://mirrors.aliyun.com/docker-ce/linux/centos/docker-ce.repo

# 安装 Docker 引擎与 Compose 插件
yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker 并设置开机自启
systemctl start docker
systemctl enable docker

# 验证
docker --version
docker compose version
```

应看到类似：`Docker version 24.x.x` 和 `Docker Compose version v2.x.x`。若使用插件，命令为 `docker compose`（空格）。

### 5.2 若 yum 报错 "No package docker-compose-plugin available"

部分 CentOS 7 源可能未包含 `docker-compose-plugin`，可改用独立版 Docker Compose：

```bash
# 只安装 Docker 引擎（不装 compose-plugin）
yum install -y docker-ce docker-ce-cli containerd.io
systemctl start docker && systemctl enable docker

# 安装 Docker Compose 独立版（v2 兼容）
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# 验证（插件方式为 docker compose；独立二进制为 docker-compose）
docker compose version
```

---

## 六、上传项目代码

### 方式 A：Git 克隆（推荐）

```bash
cd /opt
git clone <你的仓库地址> spare_part_system
cd spare_part_system
```

将 `<你的仓库地址>` 替换为实际 Git 地址；若为私有仓库，需先配置 SSH 密钥或凭据。

### 方式 B：本地上传（scp）

在**本地电脑**执行（在项目上一级目录）：

```bash
# 打包（排除 node_modules、.env、__pycache__ 等）
tar --exclude='node_modules' --exclude='.git' --exclude='__pycache__' --exclude='.env' --exclude='uploads' -czvf spare_part_system.tar.gz spare_part_system

# 上传到服务器
scp spare_part_system.tar.gz root@你的服务器IP:/opt/

# 在服务器上解压
ssh root@你的服务器IP "cd /opt && tar -xzvf spare_part_system.tar.gz && rm spare_part_system.tar.gz"
```

**上述排除项不会影响程序完整性**（本部署使用 Docker Compose 构建并运行）：
- **node_modules**：前端依赖在镜像构建时由 `npm ci` 安装，无需打包。
- **.git**：仅版本历史，运行不需要。
- **__pycache__**：Python 运行时会自动生成，无需打包。
- **.env**：敏感配置不随包上传；在服务器上按「六、配置环境变量」复制 `.env.example` 为 `.env` 即可。
- **uploads**：上传目录；新部署为空，若需迁移旧数据可单独拷贝。

然后 SSH 登录服务器：

```bash
cd /opt/spare_part_system
```

---

## 七、配置环境变量

本方案 **维持项目当前默认密码与配置，不做变动**。仅需确保存在 `.env` 供 docker-compose 读取（未设置项使用 `docker-compose.yml` 中的默认值）。

```bash
# 在项目根目录
cd /opt/spare_part_system   # 按实际路径修改

# 若无 .env，从示例复制即可（不修改即使用项目当前默认）
cp .env.example .env
```

若希望与 1.2 节默认密码表完全一致（尤其 MinIO），可在 `.env` 中增加（不修改即使用 compose 内建默认）：

- `MINIO_ROOT_USER=admin`
- `MINIO_ROOT_PASSWORD=06002336fwbMINIO`

**可选**（仅在需要时修改）：

- 若从白码自定义页跳转或 iframe 嵌入且遇 CORS 问题，可设置 `CORS_ORIGINS=白码访问的域名`。
- 若已绑定域名并启用 HTTPS，可设置 `CORS_ORIGINS`、`FRONTEND_URL` 为 `https://你的域名`。

**不要将 `.env` 提交到 Git**。

---

## 八、创建 Nginx 挂载目录（可选）

若 `nginx/conf.d`、`nginx/ssl` 不存在，Docker Compose 会按需创建；也可提前创建避免权限问题：

```bash
mkdir -p nginx/conf.d nginx/ssl
```

---

## 九、加载镜像并启动服务

### 工厂无外网时：先加载离线镜像

若已按 **「四、离线镜像准备」** 在它机导出镜像，先将 tar 拷贝到工厂服务器（如 `/opt/spare_part_images.tar`），在项目根目录执行：

```bash
docker load -i /opt/spare_part_images.tar
```

加载完成后再启动服务（见下方）。

### 启动服务

在项目根目录执行（Docker Compose 1.29.1 使用 **`docker-compose`** 命令）：

**无外网（已加载镜像）**：
```bash
docker-compose up -d --no-build
```
`--no-build` 避免再次尝试拉取或构建镜像。

**有外网**：
```bash
docker-compose up -d
```

首次会拉取镜像并构建，可能需要数分钟。查看状态：

```bash
docker-compose ps
```

应看到 `mysql`、`redis`、`minio`、`fastapi`、`frontend`、`nginx` 等为 **running**（`django-admin`、`celery-worker` 若存在也应为运行中）。

本项目 **Nginx 已配置为 8080/8443**（见 1.2），白码自定义页中的跳转链接填：**`http://你的服务器IP:8080`**（HTTPS 则为 `https://你的服务器IP:8443` 或域名）。

---

## 十、验证部署

1. **查看容器与日志**：
   ```bash
   docker-compose ps
   docker-compose logs fastapi --tail 50
   ```

2. **健康检查**（在服务器上）：
   ```bash
   curl http://127.0.0.1:8000/health
   ```
   应返回 `{"status":"ok"}` 或类似。

3. **浏览器访问**：
   - 本系统对外端口为 **8080**：`http://你的服务器公网IP:8080`
   - 若配置了 HTTPS：`https://你的服务器IP:8443` 或域名

4. **从白码跳转**：在白码自定义页配置链接或 iframe 地址为 **`http://你的服务器IP:8080`**（见 [白码对接与部署方案.md](白码对接与部署方案.md)），确认能正常打开并登录。

5. **登录**：使用默认管理员 **admin / admin123** 登录（密码维持项目当前设置）。

---

## 十一、HTTPS 与域名

白码平台使用 HTTPS，若以 iframe 方式嵌入备件系统，**备件系统也必须使用 HTTPS**，否则浏览器会报 Mixed Content 错误。有两种方案：

### 方案 A：子域名反向代理（推荐，隐藏服务器 IP）

通过白码 Nginx 反向代理为备件系统分配子域名（如 `spare.haodaapp.yxjyc.com`），不暴露服务器 IP，无自签名证书问题。

1. 配置 DNS：将 `spare.haodaapp.yxjyc.com` A 记录指向服务器 IP
2. 在白码 Nginx 配置目录中添加反向代理配置（模板见 `nginx/baima-reverse-proxy.conf.example`）
3. 若无通配符证书，使用 Let's Encrypt 为子域名申请：`certbot certonly --nginx -d spare.haodaapp.yxjyc.com`
4. 重启白码 Nginx：`nginx -t && nginx -s reload`
5. 在白码 iframe 地址填：`https://spare.haodaapp.yxjyc.com/`
6. 可选：在 `.env` 中设置 `CORS_ORIGINS=https://spare.haodaapp.yxjyc.com`

> 详细步骤见 [白码对接与部署方案.md](白码对接与部署方案.md) 「四、白码 iframe 嵌入」。

### 方案 B：自签名证书 + IP 直连（应急）

无法修改白码 Nginx 时的临时方案（暴露 IP，每个用户需手动信任证书）：

1. 生成自签名证书：`bash ssl/generate-cert.sh`
2. 重启 Nginx：`docker-compose restart nginx`
3. 用户首次需在浏览器中访问 `https://服务器IP:8443/` 并信任证书
4. 在白码 iframe 地址填：`https://服务器IP:8443/`

---

## 十二、常用运维命令（Docker Compose 1.29.1）

以下均使用 **`docker-compose`**（带连字符），与 1.29.1 一致。

| 操作           | 命令 |
|----------------|------|
| 启动全部服务   | `docker-compose up -d` |
| 停止全部服务   | `docker-compose down` |
| 查看状态       | `docker-compose ps` |
| 查看某服务日志 | `docker-compose logs -f fastapi` |
| 重启某服务     | `docker-compose restart fastapi` |
| 重新构建并启动 | `docker-compose up -d --build` |

---

## 十三、CentOS 7 常见问题

**1. Docker 无法启动或报 storage-driver 相关错误**

- 确认内核支持 overlay2：`uname -r`（建议 3.10.0-693+）。
- 可尝试在 `/etc/docker/daemon.json` 中指定存储驱动后重启 Docker：
  ```json
  { "storage-driver": "overlay2" }
  ```

**2. 防火墙已放行但仍无法访问 8080**

- 本系统 Web 端口为 **8080**（80 已被白码占用）。检查云厂商安全组是否放行 **8080**、**8443**。
- 确认 Nginx 容器在运行：`docker-compose ps nginx`。

**4. 容器内无法解析主机名（如 mysql、redis）**

- 一般为 Docker 网络正常，无需改 hosts；若使用 `network_mode: host` 需注意端口冲突。

**5. yum 安装 Docker 时提示 "Cannot retrieve metalink"**

- 可暂时禁用 fastestmirror：编辑 `/etc/yum/pluginconf.d/fastestmirror.conf`，将 `enabled=1` 改为 `enabled=0`，再执行 `yum install ...`。

**6. 磁盘空间不足**

- 清理未使用镜像：`docker system prune -a`（会删除未使用的镜像，谨慎操作）。
- 确保 `/var/lib/docker` 所在分区有足够空间。

---

## 十四、部署后检查清单

- [ ] `docker-compose ps` 各服务为 running
- [ ] 使用 **admin / admin123** 能登录（密码维持项目当前设置）
- [ ] 浏览器访问 **`http://服务器IP:8080`** 正常
- [ ] 从白码自定义页跳转能打开本系统并登录
- [ ] 前端页面与接口（列表、领用、库存等）正常
- [ ] 图片上传与查看正常
- [ ] 若遇 CORS 或域名需求，再按需配置 `.env` 中 CORS_ORIGINS、FRONTEND_URL
- [ ] 已规划数据库与 MinIO 的定期备份

更多安全与账户说明见项目根目录 **`DEPLOY.md`**；白码对接方式见 [白码对接与部署方案.md](白码对接与部署方案.md)。

---

**文档版本**：1.5
**适用系统**：CentOS 7.x
**适用场景**：工厂服务器无外网；白码已占用 80 端口；本项目使用当前端口（Nginx 8080/8443）；所有密码维持项目当前设置；与白码同机，通过白码自定义页跳转访问。
