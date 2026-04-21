<template>
  <div class="user-manage-page">
    <h2>用户管理</h2>
    <p class="page-desc">管理用户账号、模块权限与角色。<strong>权限分配顺序</strong>：先配置模块权限（只读/可编辑），再分配角色。模块权限决定用户对数据的操作范围，角色决定用户可见的功能页面及用户管理能力。</p>

    <div class="toolbar">
      <el-button type="primary" :loading="batchUploading" @click="batchUploadInput?.click()">
        批量新增用户
      </el-button>
      <el-button type="success" :loading="createSaving" @click="openCreateUserDialog">
        新建用户
      </el-button>
      <input
        ref="batchUploadInput"
        type="file"
        accept=".xlsx"
        style="display: none"
        @change="handleBatchFileChange"
      />
    </div>
    <el-card class="table-card" shadow="never">
      <!-- 移动端：卡片列表 -->
      <div v-if="isMobile" class="user-card-list" v-loading="loading">
        <div v-for="row in users" :key="row.id" class="user-card">
          <div class="user-card-header">
            <span class="user-card-name">{{ row.username }}</span>
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">{{ roleLabel(row.role) }}</el-tag>
            <el-tag :type="row.status === 'approved' ? 'success' : 'warning'" size="small">{{ statusLabel(row.status) }}</el-tag>
          </div>
          <div v-if="row.real_name" class="user-card-real-name">真实姓名：{{ row.real_name }}</div>
          <div class="user-card-meta">
            <span v-if="row.wechat_name">企业微信: {{ row.wechat_name }}</span>
            <span class="user-card-time">{{ formatDateTime(row.created_at) || '—' }}</span>
          </div>
          <div class="user-card-actions">
            <template v-if="row.status === 'pending'">
              <template v-for="opt in approveRoleOptions" :key="opt.value">
                <el-button
                  type="success"
                  size="small"
                  @click="opt.value === 'general_staff' ? openApproveGenStaffDialog(row) : handleApprove(row, opt.value)"
                >{{ opt.label }}</el-button>
              </template>
              <el-popconfirm title="确定拒绝？" @confirm="handleReject(row)">
                <template #reference>
                  <el-button type="danger" size="small">拒绝</el-button>
                </template>
              </el-popconfirm>
            </template>
            <template v-else-if="row.id !== currentUserId && row.username !== 'admin'">
              <!-- 通用人员：模块管理员只能配置权限 -->
              <template v-if="row.role === 'general_staff' && !isSuperAdmin">
                <el-tag type="warning" size="small" style="margin-right: 8px">通用人员</el-tag>
                <el-button
                  v-if="canConfigurePermForRow(row)"
                  type="primary"
                  size="small"
                  plain
                  @click="openPermDialog(row)"
                >
                  模块权限
                </el-button>
              </template>
              <template v-else>
                <el-select
                  v-model="roleMap[row.id]"
                  placeholder="修改角色"
                  size="small"
                  style="width: 100%; margin-bottom: 8px"
                  @change="(v) => handleRoleChange(row, v)"
                >
                  <el-option v-for="opt in editRoleOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                </el-select>
                <el-button
                  v-if="canConfigurePermForRow(row)"
                  type="primary"
                  size="small"
                  plain
                  style="margin-right: 8px; margin-bottom: 8px"
                  @click="openPermDialog(row)"
                >
                  模块权限
                </el-button>
                <el-popconfirm v-if="canDeleteRow(row)" title="确定删除？" @confirm="handleDelete(row)">
                  <template #reference>
                    <el-button type="danger" size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </template>
            <template v-else>
              <el-tag type="info" size="small">{{ row.id === currentUserId ? '当前用户（不可修改）' : 'admin（不可删除）' }}</el-tag>
            </template>
          </div>
        </div>
      </div>
      <!-- PC 端：表格 -->
      <el-table
        v-else
        v-loading="loading"
        :data="users"
        border
        stripe
        style="width: 100%"
        max-height="520"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" sortable />
        <el-table-column prop="username" label="用户名" min-width="140" sortable />
        <el-table-column prop="real_name" label="真实姓名" min-width="100" sortable show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.real_name || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="wechat_name" label="企业微信名" min-width="120" sortable>
          <template #default="{ row }">
            {{ row.wechat_name || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="140" align="center" sortable>
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center" sortable>
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : 'warning'" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" align="center" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) || '—' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="400" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <span class="op-pending-label">待审核</span>
              <template v-for="opt in approveRoleOptions" :key="opt.value">
                <el-button
                  type="success"
                  size="small"
                  @click="opt.value === 'general_staff' ? openApproveGenStaffDialog(row) : handleApprove(row, opt.value)"
                >
                  {{ opt.label }}
                </el-button>
              </template>
              <el-popconfirm
                title="确定拒绝此注册申请？拒绝将删除该用户记录。"
                confirm-button-text="拒绝"
                cancel-button-text="取消"
                @confirm="handleReject(row)"
              >
                <template #reference>
                  <el-button type="danger" size="small">拒绝</el-button>
                </template>
              </el-popconfirm>
            </template>
            <template v-else>
              <template v-if="row.id === currentUserId">
                <el-tag type="danger" size="small">当前用户（不可修改）</el-tag>
              </template>
              <template v-else-if="row.username === 'admin'">
                <el-tag type="info" size="small">admin（不可删除）</el-tag>
              </template>
              <!-- 通用人员：模块管理员只能配置权限，不能改角色/删除 -->
              <template v-else-if="row.role === 'general_staff' && !isSuperAdmin">
                <el-tag type="warning" size="small" style="margin-right: 8px">通用人员</el-tag>
                <el-button
                  v-if="canConfigurePermForRow(row)"
                  type="primary"
                  size="small"
                  plain
                  @click="openPermDialog(row)"
                >
                  模块权限
                </el-button>
              </template>
              <template v-else>
                <el-select
                  v-model="roleMap[row.id]"
                  placeholder="修改角色"
                  size="small"
                  style="width: 140px"
                  @change="(v) => handleRoleChange(row, v)"
                >
                  <el-option v-for="opt in editRoleOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
                </el-select>
                <el-button
                  v-if="canConfigurePermForRow(row)"
                  type="primary"
                  size="small"
                  plain
                  style="margin-left: 8px"
                  @click="openPermDialog(row)"
                >
                  模块权限
                </el-button>
                <el-popconfirm
                  v-if="canDeleteRow(row)"
                  title="确定删除该用户？删除后不可恢复。"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="handleDelete(row)"
                >
                  <template #reference>
                    <el-button type="danger" size="small" style="margin-left: 8px">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <div class="total-tip">共 {{ users.length }} 个用户</div>
    </el-card>

    <!-- 模块权限配置弹窗 -->
    <el-dialog
      v-model="permDialogVisible"
      :title="`配置模块权限 — ${permTarget?.username ?? ''}`"
      :width="isMobile ? undefined : '520px'"
      :fullscreen="isMobile"
      destroy-on-close
      append-to-body
      class="perm-dialog"
      :class="{ 'perm-dialog--mobile': isMobile }"
    >
      <div v-if="permDialogModules.length === 0" class="perm-empty">
        <el-empty description="当前暂无可配置的模块" :image-size="80" />
      </div>
      <template v-else>
        <p class="perm-dialog-desc">
          为 <strong>{{ permTarget?.username }}</strong> 配置各模块的访问权限。
          <template v-if="!isSuperAdmin">
            <br /><span style="color: #E6A23C; font-size: 12px;">您作为模块管理员，可为本模块用户授予「只读」或「可编辑」权限。</span>
          </template>
        </p>
        <el-table :data="permDialogModules" border size="small" style="width: 100%">
          <el-table-column prop="name" label="模块" min-width="130" />
          <el-table-column label="权限级别" width="200" align="center">
            <template #default="{ row: mod }">
              <el-select
                v-model="permEditMap[mod.id]"
                placeholder="不授权"
                size="small"
                clearable
                style="width: 140px"
              >
                <el-option
                  v-for="lv in permDialogLevelOptions"
                  :key="lv.value"
                  :label="lv.label"
                  :value="lv.value"
                />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
        <div class="perm-level-legend">
          <span><strong>可编辑</strong>：可查看、查询、增删改所有数据（用户管理权限由角色决定）</span>
          <span><strong>只读</strong>：仅可查看、查询、导出，不可增删改</span>
        </div>
      </template>
      <template #footer>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button
          v-if="permDialogModules.length > 0"
          type="primary"
          :loading="permSaving"
          @click="savePermissions"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 通用人员审批弹窗：同步分配初始模块权限 -->
    <el-dialog
      v-model="approveGenStaffDialogVisible"
      :title="`审批通过为通用人员 — ${approveGenStaffTarget?.wechat_name || approveGenStaffTarget?.username || ''}`"
      width="520px"
      destroy-on-close
    >
      <div v-if="newModules.length === 0">
        <el-alert
          title="当前暂无可配置的扩展模块，通用人员审批后将无任何模块访问权限，后续可通过「模块权限」按钮进行配置。"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />
      </div>
      <template v-else>
        <p class="perm-dialog-desc">
          将 <strong>{{ approveGenStaffTarget?.wechat_name || approveGenStaffTarget?.username }}</strong> 审批为通用人员，并设置初始模块权限。
          未选择权限的模块将无法访问（后续可修改）。
        </p>
        <el-table :data="newModules" border size="small" style="width: 100%">
          <el-table-column prop="name" label="模块" min-width="120" />
          <el-table-column label="初始权限" width="180" align="center">
            <template #default="{ row: mod }">
              <el-select
                v-model="approveGenStaffPermMap[mod.id]"
                placeholder="不授权"
                size="small"
                clearable
                style="width: 130px"
              >
                <el-option v-for="lv in PERM_LEVEL_OPTIONS" :key="lv.value" :label="lv.label" :value="lv.value" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
        <div class="perm-level-legend" style="margin-top: 12px">
          <span><strong>可编辑</strong>：可查看、查询、增删改所有数据</span>
          <span><strong>只读</strong>：仅可查看、查询、导出，不可增删改</span>
        </div>
      </template>
      <template #footer>
        <el-button @click="approveGenStaffDialogVisible = false">取消</el-button>
        <el-button type="success" :loading="approveGenStaffSaving" @click="confirmApproveGenStaff">
          确认通过
        </el-button>
      </template>
    </el-dialog>

    <!-- 新建用户弹窗 -->
    <el-dialog
      v-model="createUserDialogVisible"
      title="新建用户"
      :width="isMobile ? undefined : '520px'"
      :fullscreen="isMobile"
      destroy-on-close
      append-to-body
      class="perm-dialog"
      :class="{ 'perm-dialog--mobile': isMobile }"
      @closed="resetCreateForm"
    >
      <el-form ref="createFormRef" :model="createForm" :rules="createFormRules" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="字母、数字、下划线或中文" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="createForm.real_name" placeholder="选填" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="opt in createRoleOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <p v-if="!isSuperAdmin" class="create-role-tip">您作为模块管理员，仅可新建本模块领用员或通用人员。</p>
        </el-form-item>
        <template v-if="createPermModules.length > 0 && (createForm.role === 'general_staff' || ROLE_MODULE_REQUIREMENT[createForm.role])">
          <el-form-item label="模块权限">
            <span class="create-perm-desc">
              <template v-if="createForm.role === 'general_staff'">配置通用人员可访问的模块及级别（选填，后续可改）</template>
              <template v-else>为此角色预配置模块权限（角色分配需先有模块权限）</template>
            </span>
          </el-form-item>
          <el-table :data="createPermModules" border size="small" style="width: 100%">
            <el-table-column prop="name" label="模块" min-width="120" />
            <el-table-column label="权限级别" width="180" align="center">
              <template #default="{ row: mod }">
                <el-select
                  v-model="createPermMap[mod.id]"
                  placeholder="不授权"
                  size="small"
                  clearable
                  style="width: 130px"
                >
                  <el-option
                    v-for="lv in createPermLevelOptions"
                    :key="lv.value"
                    :label="lv.label"
                    :value="lv.value"
                  />
                </el-select>
              </template>
            </el-table-column>
          </el-table>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="createUserDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="submitCreateUser">确定新建</el-button>
      </template>
    </el-dialog>

    <!-- 新建用户成功：设置密码链接 -->
    <el-dialog
      v-model="createResultVisible"
      title="新建成功"
      width="560px"
      destroy-on-close
    >
      <p class="batch-links-title">请将以下设置密码链接发给该用户（链接 7 天内有效）：</p>
      <div v-if="createResult" class="batch-link-row">
        <span class="batch-username">{{ createResult.username }}{{ createResult.real_name ? `（${createResult.real_name}）` : '' }}</span>
        <el-input
          :model-value="getSetupLink(createResult.token)"
          readonly
          size="small"
          class="batch-link-input"
        >
          <template #append>
            <el-button size="small" @click="copySetupLink(createResult!.token)">复制</el-button>
          </template>
        </el-input>
      </div>
      <template #footer>
        <el-button type="primary" @click="createResultVisible = false; fetchUsers()">关闭并刷新</el-button>
      </template>
    </el-dialog>

    <!-- 批量新增结果弹窗 -->
    <el-dialog
      v-model="batchResultVisible"
      title="批量新增结果"
      width="560px"
      destroy-on-close
    >
      <p v-if="batchResult">成功 {{ batchResult.created }} 个，失败 {{ batchResult.failed }} 个</p>
      <div v-if="batchResult?.items?.length" class="batch-links">
        <p class="batch-links-title">请将以下设置密码链接发给对应用户（链接 7 天内有效）：</p>
        <div v-for="item in batchResult.items" :key="item.username" class="batch-link-row">
          <span class="batch-username">{{ item.username }}{{ item.real_name ? `（${item.real_name}）` : '' }}</span>
          <el-input
            :model-value="getSetupLink(item.token)"
            readonly
            size="small"
            class="batch-link-input"
          >
            <template #append>
              <el-button size="small" @click="copySetupLink(item.token)">复制</el-button>
            </template>
          </el-input>
        </div>
      </div>
      <div v-if="batchResult?.errors?.length" class="batch-errors">
        <p class="batch-errors-title">失败行：</p>
        <ul>
          <li v-for="(err, i) in batchResult.errors" :key="i">第 {{ err.row }} 行 {{ err.username }}：{{ err.error }}</li>
        </ul>
      </div>
      <template #footer>
        <el-button type="primary" @click="batchResultVisible = false; fetchUsers()">关闭并刷新</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'UserManage'
})

import { ref, reactive, onMounted, computed } from 'vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { userApi, type UserListItem, ROLE_LABELS, type UserRole, type BatchCreateUsersResult, type AdminCreateUserResult } from '@/api/user'
import { formatDateTime } from '@/utils/date'
import { ALL_MODULES, NEW_MODULES, PERM_LEVEL_OPTIONS, ROLE_MANAGED_MODULES } from '@/utils/modules'

const authStore = useAuthStore()
const { isMobile } = useIsMobile()
const currentUserId = computed(() => authStore.user?.id ?? null)
const isSuperAdmin = computed(() => authStore.isSuperAdmin)
const isElectricalAdmin = computed(() => authStore.isElectricalAdmin)
const isMechanicalAdmin = computed(() => authStore.isMechanicalAdmin)

/** 当前用户是否可删除该行：超级管理员可删非 admin 且非自己；电气管理员仅可删电气领用员；机械管理员仅可删机械领用员 */
function canDeleteRow(row: UserListItem): boolean {
  if (row.id === currentUserId.value) return false
  if (row.username === 'admin') return false
  if (authStore.user?.username === 'admin') return true
  if (isElectricalAdmin.value && row.role === 'electrical_requisition_clerk') return true
  if (isMechanicalAdmin.value && row.role === 'mechanical_requisition_clerk') return true
  return false
}

/** 分配以下角色前，用户须先具备对应模块权限（先设模块权限，再分配角色） */
const ROLE_MODULE_REQUIREMENT: Record<string, { module: string; label: string }> = {
  electrical_admin:             { module: 'electrical', label: '电气备件' },
  electrical_requisition_clerk: { module: 'electrical', label: '电气备件' },
  mechanical_admin:             { module: 'mechanical', label: '机械备件' },
  mechanical_requisition_clerk: { module: 'mechanical', label: '机械备件' },
}

/** 检查目标用户是否已具备指定模块权限（通过 permissions JSON 或角色） */
function userHasModuleAccess(row: UserListItem, moduleId: string): boolean {
  if (row.permissions && moduleId in row.permissions) return true
  if (moduleId === 'electrical' && ['electrical_admin', 'electrical_requisition_clerk', 'requisition_clerk'].includes(row.role)) return true
  if (moduleId === 'mechanical' && ['mechanical_admin', 'mechanical_requisition_clerk'].includes(row.role)) return true
  return false
}

const loading = ref(false)
const users = ref<UserListItem[]>([])
const roleMap = reactive<Record<number, string>>({})

const batchUploadInput = ref<HTMLInputElement | null>(null)
const batchUploading = ref(false)
const batchResultVisible = ref(false)
const batchResult = ref<BatchCreateUsersResult | null>(null)

// 新建用户
const createUserDialogVisible = ref(false)
const createFormRef = ref<InstanceType<typeof import('element-plus').Form> | null>(null)
const createForm = reactive({ username: '', real_name: '', role: '' as UserRole | '' })
const createFormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}
const createPermMap = reactive<Record<string, string>>({})
const createSaving = ref(false)
const createResultVisible = ref(false)
const createResult = ref<AdminCreateUserResult | null>(null)

/** 新建用户时可选角色：超级管理员任意；电气/机械管理员仅本模块领用员或通用人员 */
const createRoleOptions = computed(() => {
  if (authStore.user?.username === 'admin') {
    return [
      { label: '超级管理员', value: 'admin' },
      { label: '电气领用员', value: 'electrical_requisition_clerk' },
      { label: '机械领用员', value: 'mechanical_requisition_clerk' },
      { label: '电气管理员', value: 'electrical_admin' },
      { label: '机械管理员', value: 'mechanical_admin' },
      { label: '通用人员', value: 'general_staff' },
    ]
  }
  if (isElectricalAdmin.value) {
    return [
      { label: '电气领用员', value: 'electrical_requisition_clerk' },
      { label: '通用人员', value: 'general_staff' },
    ]
  }
  if (isMechanicalAdmin.value) {
    return [
      { label: '机械领用员', value: 'mechanical_requisition_clerk' },
      { label: '通用人员', value: 'general_staff' },
    ]
  }
  return []
})
const createPermModules = computed(() => permDialogModules.value)
const createPermLevelOptions = computed(() => permDialogLevelOptions.value)

function openCreateUserDialog() {
  createForm.username = ''
  createForm.real_name = ''
  createForm.role = ''
  ALL_MODULES.forEach((m) => { createPermMap[m.id] = '' })
  createUserDialogVisible.value = true
}

function resetCreateForm() {
  createForm.username = ''
  createForm.real_name = ''
  createForm.role = ''
  ALL_MODULES.forEach((m) => { createPermMap[m.id] = '' })
}

async function submitCreateUser() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  if (!createForm.username.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!createForm.role) {
    ElMessage.warning('请选择角色')
    return
  }
  const permissions: Record<string, string> = {}
  if (createForm.role === 'general_staff') {
    // 通用人员：使用用户选择的模块权限
    createPermModules.value.forEach((m) => {
      if (createPermMap[m.id]) permissions[m.id] = createPermMap[m.id]
    })
  } else {
    // 模块角色（领用员/管理员）：若未配置对应模块权限，自动按角色级别预填
    const req = ROLE_MODULE_REQUIREMENT[createForm.role]
    if (req) {
      const autoLevel = ['electrical_admin', 'mechanical_admin'].includes(createForm.role) ? 'editor' : 'viewer'
      if (createPermMap[req.module]) {
        permissions[req.module] = createPermMap[req.module]
      } else {
        permissions[req.module] = autoLevel
      }
    }
  }
  createSaving.value = true
  try {
    const res = await userApi.createUser({
      username: createForm.username.trim(),
      real_name: createForm.real_name?.trim() || undefined,
      role: createForm.role as UserRole,
      permissions: Object.keys(permissions).length ? permissions : undefined,
    })
    createResult.value = res
    createResultVisible.value = true
    createUserDialogVisible.value = false
    ElMessage.success(`已新建用户 ${res.username}，请将设置密码链接发给该用户`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '新建失败')
  } finally {
    createSaving.value = false
  }
}

// 模块权限弹窗
const permDialogVisible = ref(false)
const permTarget = ref<UserListItem | null>(null)
const permEditMap = reactive<Record<string, string>>({})
const permSaving = ref(false)

/** 当前操作者可在弹窗中配置的模块列表：超级管理员全部模块；模块管理员仅自己管辖的模块 */
const permDialogModules = computed(() => {
  if (authStore.isSuperAdmin) return ALL_MODULES
  const managed = ROLE_MANAGED_MODULES[authStore.user?.role ?? '']
  if (managed) return ALL_MODULES.filter((m) => managed.modules.includes(m.id))
  return []
})

/** 当前操作者可选的最高权限级别：超级管理员全部；模块管理员最高 editor */
const permDialogLevelOptions = computed(() => {
  if (authStore.isSuperAdmin) return PERM_LEVEL_OPTIONS
  const managed = ROLE_MANAGED_MODULES[authStore.user?.role ?? '']
  if (managed) return PERM_LEVEL_OPTIONS.filter((o) => o.value !== 'admin')
  return []
})

/** 是否可以为某行用户配置模块权限 */
function canConfigurePermForRow(row: UserListItem): boolean {
  if (row.id === currentUserId.value) return false
  if (row.username === 'admin') return false
  if (authStore.isSuperAdmin) return true
  // 模块管理员可为本模块内任何非管理员角色的用户配置模块权限
  if (authStore.isElectricalAdmin || authStore.isMechanicalAdmin) {
    if (['electrical_admin', 'mechanical_admin'].includes(row.role)) return false
    return true
  }
  return false
}

/** 已弃用引用（保留供 approveGenStaffDialog 使用） */
const newModules = computed(() => NEW_MODULES)

// 通用人员审批弹窗
const approveGenStaffDialogVisible = ref(false)
const approveGenStaffTarget = ref<UserListItem | null>(null)
const approveGenStaffPermMap = reactive<Record<string, string>>({})
const approveGenStaffSaving = ref(false)

function openPermDialog(row: UserListItem) {
  permTarget.value = row
  // 初始化编辑映射：所有模块均填入（空字符串代表无权限）
  ALL_MODULES.forEach((m) => {
    permEditMap[m.id] = row.permissions?.[m.id] ?? ''
  })
  permDialogVisible.value = true
}

async function savePermissions() {
  if (!permTarget.value) return
  // 将当前可配置的模块发送给后端（含空值以便后端做删除合并）
  const payload: Record<string, string> = {}
  permDialogModules.value.forEach((m) => {
    payload[m.id] = permEditMap[m.id] || ''
  })
  permSaving.value = true
  try {
    const updated = await userApi.updatePermissions(permTarget.value.id, payload)
    const row = users.value.find((u) => u.id === permTarget.value!.id)
    if (row) row.permissions = updated.permissions
    ElMessage.success('模块权限已保存')
    permDialogVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    permSaving.value = false
  }
}

function getSetupLink(token: string) {
  if (typeof window === 'undefined') return ''
  const base = import.meta.env.BASE_URL
  const path = base.endsWith('/') ? `${base}set-password` : `${base}/set-password`
  return `${window.location.origin}${path}?token=${encodeURIComponent(token)}`
}

function copySetupLink(token: string) {
  const link = getSetupLink(token)
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(link).then(() => ElMessage.success('已复制到剪贴板')).catch(() => fallbackCopy(link))
  } else {
    fallbackCopy(link)
  }
}
function fallbackCopy(text: string) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  try {
    document.execCommand('copy')
    ElMessage.success('已复制到剪贴板')
  } finally {
    document.body.removeChild(ta)
  }
}

async function handleBatchFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.xlsx')) {
    ElMessage.warning('批量导入仅支持 .xlsx 文件，请先另存为 xlsx 后再上传')
    return
  }
  batchUploading.value = true
  batchResult.value = null
  try {
    const res = await userApi.batchCreateUsers(file)
    batchResult.value = res
    batchResultVisible.value = true
    if (res.created > 0) ElMessage.success(`成功创建 ${res.created} 个用户，请将设置密码链接发给对应用户`)
    if (res.failed > 0) ElMessage.warning(`${res.failed} 行导入失败`)
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '批量导入失败')
  } finally {
    batchUploading.value = false
  }
}

function roleLabel(r: string) {
  return ROLE_LABELS[r] || r || '—'
}

/** 审批时可选的角色：超级管理员任意（含通用人员）；电气管理员仅电气领用员；机械管理员仅机械领用员 */
const approveRoleOptions = computed(() => {
  if (authStore.user?.username === 'admin') {
    return [
      { label: '通过为电气领用员', value: 'electrical_requisition_clerk' as UserRole },
      { label: '通过为机械领用员', value: 'mechanical_requisition_clerk' as UserRole },
      { label: '通过为电气管理员', value: 'electrical_admin' as UserRole },
      { label: '通过为机械管理员', value: 'mechanical_admin' as UserRole },
      { label: '通过为通用人员', value: 'general_staff' as UserRole },
      { label: '通过为超级管理员', value: 'admin' as UserRole },
    ]
  }
  if (isElectricalAdmin.value) return [{ label: '通过为电气领用员', value: 'electrical_requisition_clerk' as UserRole }]
  if (isMechanicalAdmin.value) return [{ label: '通过为机械领用员', value: 'mechanical_requisition_clerk' as UserRole }]
  return []
})

/** 修改角色时的下拉选项 */
const editRoleOptions = computed(() => {
  if (authStore.user?.username === 'admin') {
    return [
      { label: '超级管理员', value: 'admin' },
      { label: '电气领用员', value: 'electrical_requisition_clerk' },
      { label: '机械领用员', value: 'mechanical_requisition_clerk' },
      { label: '电气管理员', value: 'electrical_admin' },
      { label: '机械管理员', value: 'mechanical_admin' },
      { label: '通用人员', value: 'general_staff' },
    ]
  }
  if (isElectricalAdmin.value) return [{ label: '电气领用员', value: 'electrical_requisition_clerk' }]
  if (isMechanicalAdmin.value) return [{ label: '机械领用员', value: 'mechanical_requisition_clerk' }]
  return []
})

function statusLabel(s: string) {
  if (s === 'approved') return '已审批'
  if (s === 'pending') return '待审批'
  return s || '—'
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await userApi.list()
    users.value = Array.isArray(res) ? res : []
    users.value.forEach((u) => {
      roleMap[u.id] = u.role
    })
  } catch {
    ElMessage.error('获取用户列表失败')
    users.value = []
  } finally {
    loading.value = false
  }
}

async function handleRoleChange(row: UserListItem, newRole: string) {
  if (newRole === row.role) return
  // 模块权限先行：分配模块角色前校验用户是否已有对应模块权限
  const req = ROLE_MODULE_REQUIREMENT[newRole]
  if (req && !userHasModuleAccess(row, req.module)) {
    roleMap[row.id] = row.role
    ElMessage.warning(`请先为 ${row.username} 配置「${req.label}」模块权限（只读或可编辑），再分配此角色`)
    return
  }
  try {
    await userApi.updateRole(row.id, newRole as UserRole)
    row.role = newRole
    ElMessage.success(`已更新 ${row.username} 为 ${roleLabel(newRole)}`)
  } catch (e: any) {
    roleMap[row.id] = row.role
    ElMessage.error(e?.response?.data?.detail || '更新角色失败')
  }
}

function openApproveGenStaffDialog(row: UserListItem) {
  approveGenStaffTarget.value = row
  NEW_MODULES.forEach((m) => {
    approveGenStaffPermMap[m.id] = ''
  })
  approveGenStaffDialogVisible.value = true
}

async function confirmApproveGenStaff() {
  if (!approveGenStaffTarget.value) return
  const perms: Record<string, string> = {}
  NEW_MODULES.forEach((m) => {
    if (approveGenStaffPermMap[m.id]) perms[m.id] = approveGenStaffPermMap[m.id]
  })
  approveGenStaffSaving.value = true
  try {
    await userApi.approve(approveGenStaffTarget.value.id, 'general_staff', perms)
    ElMessage.success(`已通过 ${approveGenStaffTarget.value.wechat_name || approveGenStaffTarget.value.username} 的注册申请，并设为通用人员`)
    approveGenStaffDialogVisible.value = false
    await fetchUsers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '审批失败')
  } finally {
    approveGenStaffSaving.value = false
  }
}

async function handleApprove(row: UserListItem, role: UserRole) {
  // 模块权限先行：审批为模块角色前校验用户是否已有对应模块权限
  const req = ROLE_MODULE_REQUIREMENT[role]
  if (req && !userHasModuleAccess(row, req.module)) {
    ElMessage.warning(`请先为该用户配置「${req.label}」模块权限（只读或可编辑），再审批为此角色`)
    return
  }
  try {
    await userApi.approve(row.id, role)
    ElMessage.success(`已通过 ${row.wechat_name || row.username} 的注册申请，并设为 ${roleLabel(role)}`)
    await fetchUsers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '审批失败')
  }
}

async function handleReject(row: UserListItem) {
  try {
    await userApi.reject(row.id)
    ElMessage.success(`已拒绝 ${row.wechat_name || row.username} 的注册申请`)
    await fetchUsers()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '拒绝失败')
  }
}

async function handleDelete(row: UserListItem) {
  try {
    await userApi.delete(row.id)
    ElMessage.success(`已删除用户 ${row.wechat_name || row.username}`)
    await fetchUsers()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    const msg = Array.isArray(detail) ? detail[0]?.msg : (detail ?? '删除失败')
    ElMessage.error(typeof msg === 'string' ? msg : '删除失败')
  }
}

onMounted(fetchUsers)
</script>

<style scoped lang="scss">
.user-manage-page {
  padding: 0 20px 20px;
}

h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #303133;
}

.page-desc {
  margin: 0 0 20px;
  font-size: 14px;
  color: #606266;
}

.toolbar {
  margin-bottom: 16px;
}

.batch-links-title,
.batch-errors-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.batch-link-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.batch-username {
  flex-shrink: 0;
  width: 140px;
  font-size: 13px;
}

.batch-link-input {
  flex: 1;
  min-width: 0;
}

.batch-errors ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #606266;
}

.batch-errors li {
  margin-bottom: 4px;
}

.table-card {
  :deep(.el-card__body) {
    padding: 16px 20px;
  }
}

.total-tip {
  text-align: center;
  padding: 16px;
  font-size: 14px;
  color: #606266;
}

.op-pending-label {
  display: inline-block;
  margin-right: 8px;
  padding: 2px 8px;
  font-size: 12px;
  color: #e6a23c;
  background: #fdf6ec;
  border-radius: 4px;
}

/* 移动端用户卡片 */
.user-card-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.user-card {
  padding: 16px;
  background: linear-gradient(to bottom, #ffffff, #fafbff);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  border-left: 4px solid var(--el-color-primary-light-5);
}

.user-card-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.user-card-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.user-card-real-name {
  font-size: 13px;
  color: #303133;
  margin-bottom: 6px;
}

.user-card-meta {
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}

.user-card-time {
  display: block;
  margin-top: 4px;
}

.user-card-actions {
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.user-card-actions .el-button {
  margin-right: 8px;
  margin-bottom: 4px;
}

.perm-dialog-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.perm-level-legend {
  margin-top: 12px;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 12px;
  color: #606266;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.perm-empty {
  text-align: center;
  padding: 8px 0;
}

.perm-empty-hint {
  margin: 0 0 8px;
  font-size: 13px;
  color: #909399;
  line-height: 1.6;
  text-align: left;
  padding: 0 12px;
}

.create-role-tip {
  margin: 6px 0 0;
  font-size: 12px;
  color: #e6a23c;
}

.create-perm-desc {
  font-size: 12px;
  color: #606266;
  display: block;
  margin-top: -8px;
  margin-bottom: 8px;
}

/* 模块权限弹窗：移动端全屏可滚动，底部按钮固定，参考备件编辑弹窗设计 */
.perm-dialog--mobile :deep(.el-dialog) {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 100%;
  margin: 0 !important;
  border-radius: 0;
}
.perm-dialog--mobile :deep(.el-dialog__body) {
  padding: 16px;
  padding-bottom: 24px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}
.perm-dialog--mobile :deep(.el-dialog__footer) {
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0));
  border-top: 1px solid var(--el-border-color-lighter);
}

@media (max-width: 767px) {
  .user-manage-page {
    padding: 0 0 16px;
  }
  .user-manage-page h2 {
    font-size: 18px;
  }
  .user-manage-page .page-desc {
    font-size: 13px;
  }
  .table-card {
    border-radius: 8px;
    overflow: hidden;
  }
  .table-card :deep(.el-card__body) {
    padding: 12px;
  }
}
</style>
