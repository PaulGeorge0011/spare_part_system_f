# 批量新增用户 + 修改密码 功能 — 部署文件清单

将以下文件更新到工厂服务器即可完成本次功能发布。

---

## 后端（Backend）

| 文件路径 | 说明 |
|----------|------|
| `backend/api/app/models/user.py` | 用户表新增字段：`setup_password_token`、`setup_token_expires_at` |
| `backend/api/app/main.py` | 启动时自动迁移：为 `users` 表添加上述两列（若不存在） |
| `backend/api/app/crud/user.py` | 新增：`create_user_pending_setup`、`get_user_by_setup_token`、`set_password_by_token`、`update_user_password` |
| `backend/api/app/schemas/auth.py` | 新增请求体：`SetPasswordByTokenRequest`、`ChangePasswordRequest` |
| `backend/api/app/api/v1/auth.py` | 新增接口：`POST /auth/set-password-by-token`、`PATCH /auth/me/password` |
| `backend/api/app/api/v1/users.py` | 新增接口：`POST /users/batch`（上传 Excel 批量创建用户） |
| `backend/api/requirements.txt` | 新增依赖：`openpyxl==3.1.2` |

**后端部署后请执行：**  
在服务器上安装新依赖：`pip install openpyxl==3.1.2`（或 `pip install -r requirements.txt`）。  
重启后端服务后，应用启动时会自动为 `users` 表添加新列（若尚未存在）。

---

## 前端（Frontend）

| 文件路径 | 说明 |
|----------|------|
| `frontend/src/api/auth.ts` | 新增：`setPasswordByToken`、`changePassword` |
| `frontend/src/api/user.ts` | 新增：`batchCreateUsers` 及类型 `BatchUserItem`、`BatchCreateUsersResult` |
| `frontend/src/views/SetPassword.vue` | **新建**：通过链接设置密码页面（`/set-password?token=xxx`） |
| `frontend/src/views/UserManage.vue` | 新增：批量新增用户按钮、上传 Excel、结果弹窗（含设置密码链接复制） |
| `frontend/src/App.vue` | 新增：顶栏与抽屉中「修改密码」入口、修改密码弹窗及提交逻辑 |
| `frontend/src/router/index.ts` | 新增路由：`/set-password`（公开页） |

---

## 功能说明

1. **批量新增用户（方案 C）**  
   - 管理员在「用户管理」页点击「批量新增用户」，上传 Excel（.xlsx/.xls）。  
   - Excel 表头需包含：**账号**（或「用户名」）、**姓名**（或「真实姓名」，可选）、**角色**（如：电气领用员、机械领用员、电气管理员、机械管理员、超级管理员）。  
   - 不包含密码列；创建后用户处于「待设置密码」状态。  
   - 接口返回每个新用户的「设置密码链接」（含 token，7 天内有效）。管理员将链接发给对应用户，用户打开链接设置密码后即可登录。

2. **用户修改密码**  
   - 已登录用户可在顶栏或侧边抽屉中点击「修改密码」，在弹窗中输入当前密码、新密码并确认后提交。  
   - 修改成功后需重新登录（旧 token 失效）。

3. **通过链接设置密码**  
   - 批量创建的用户打开管理员下发的链接（形如：`https://你的域名/set-password?token=xxx`），在页面中输入新密码并确认即可完成设置，之后使用新密码登录。

---

## 部署顺序建议

1. 先部署**后端**并重启服务（确保新依赖已安装、新接口可用）。  
2. 再部署**前端**并发布前端资源。  
3. 在用户管理页上传一份测试 Excel 验证批量创建与设置密码链接是否正常；再测试已登录用户「修改密码」流程。
