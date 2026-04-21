# 登录页「修改密码」功能 — 部署修改文件清单

本次在登录页提供「修改密码」：用户通过输入**账号**、**旧密码**、**新密码**即可在未登录状态下修改密码。

---

## 一、修改过的文件列表（按路径）

| 序号 | 文件路径 | 说明 |
|------|----------|------|
| 1 | `backend/api/app/crud/user.py` | 新增 `update_user_password(db, user_id, new_password_hash)`，用于更新密码并递增 token_version |
| 2 | `backend/api/app/schemas/auth.py` | 新增请求体模型 `ChangePasswordFromLoginRequest`（username, old_password, new_password） |
| 3 | `backend/api/app/api/v1/auth.py` | 新增接口 `POST /auth/change-password`，校验账号与旧密码后调用 crud 更新密码 |
| 4 | `frontend/src/api/auth.ts` | 新增 `changePasswordFromLogin(username, oldPassword, newPassword)` 调用后端接口 |
| 5 | `frontend/src/views/Login.vue` | 登录页增加「修改密码」链接、弹窗表单（账号/旧密码/新密码/确认新密码）及提交逻辑 |

---

## 二、部署到工厂服务器时的操作建议

1. **备份**  
   更新前备份上述 5 个文件（若服务器上有修改，请一并备份）。

2. **覆盖文件**  
   将本地已修改的 5 个文件按相同路径覆盖到服务器对应目录。

3. **后端**  
   - 若使用 Docker：重新构建并启动后端容器，或直接挂载代码并重启服务。  
   - 若直接跑进程：重启 FastAPI/Uvicorn 进程使新代码生效。

4. **前端**  
   - 在服务器上对前端重新执行构建（如 `npm run build`），将生成的静态资源部署到 Nginx 或当前使用的 Web 服务器目录。

5. **验证**  
   - 打开登录页，点击「修改密码」，输入账号、旧密码、新密码并确认新密码，提交后应提示「密码已修改，请使用新密码登录」。  
   - 使用新密码登录应成功；旧密码应无法登录。

---

## 三、API 说明（供联调/排查）

- **接口**：`POST /api/v1/auth/change-password`  
- **请求体**：`{ "username": "账号", "old_password": "旧密码", "new_password": "新密码" }`  
- **成功**：HTTP 200，`{ "message": "密码已修改，请使用新密码登录" }`  
- **失败**：账号或旧密码错误返回 401；待审核用户返回 403；校验规则与登录一致（用户名格式、密码长度等）。

以上文件为本次「登录页修改密码」涉及的全部变更，按清单更新到服务器即可完成部署。
