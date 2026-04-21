/**
 * 系统模块注册表
 *
 * 所有模块（含电气/机械）均通过 User.permissions JSON 列统一配置权限。
 * 现有角色用户（electrical_admin 等）无需迁移，canAccessModule 自动推导等效级别。
 *
 * 新增管理模块时，在 ALL_MODULES 末尾追加一项，并在 router/index.ts 添加路由即可。
 */

export type ModulePermLevel = 'admin' | 'editor' | 'viewer'

export interface ModuleDefinition {
  id: string           // 唯一标识，也是 permissions JSON 的 key
  name: string
  description: string
  path: string
  iconEmoji: string
  accentColor: string
}

/**
 * 模块权限级别（可配置项，admin 级别由角色决定，不可通过权限接口设置）
 * 只读：查看、查询、导出，不可增删改
 * 可编辑：查看 + 增删改所有数据（用户管理权限由角色控制，不受此项影响）
 */
export const PERM_LEVEL_OPTIONS: { value: ModulePermLevel; label: string; tagType: string }[] = [
  { value: 'editor', label: '可编辑', tagType: 'warning' },
  { value: 'viewer', label: '只读',   tagType: 'info'    },
]

/** 权限级别顺序（数值越大权限越高） */
const LEVEL_ORDER: Record<string, number> = { viewer: 1, editor: 2, admin: 3 }

export function hasLevel(
  userLevel: string | null | undefined,
  required: ModulePermLevel,
): boolean {
  if (!userLevel) return false
  return (LEVEL_ORDER[userLevel] ?? 0) >= (LEVEL_ORDER[required] ?? 0)
}

/**
 * 系统所有模块注册表
 *
 * 添加新模块步骤：
 * 1. 在此处追加一条 ModuleDefinition
 * 2. 在 router/index.ts 添加路由（meta: { moduleId: 'xxx', minLevel: 'viewer' }）
 * 3. 在 backend/api/v1/ 添加路由文件，使用 require_module_permission() 保护接口
 * 4. 在 backend/api/app/models/ 添加数据模型
 * 5. 在 backend/api/app/main.py 注册路由
 *
 * 电气/机械权限级别含义：
 *   admin  → 完整管理（备件增删改、库存、报表、可配置本模块通用人员权限）
 *   editor → 备件增删改、领用申请（不含库存/报表/用户管理）
 *   viewer → 查看备件、提交领用申请（只读）
 */
export const ALL_MODULES: ModuleDefinition[] = [
  {
    id: 'electrical',
    name: '电气备件管理',
    description: '电气设备备件库存管理、领用申请及报表统计',
    path: '/electrical',
    iconEmoji: '⚡',
    accentColor: '#409EFF',
  },
  {
    id: 'mechanical',
    name: '机械备件管理',
    description: '机械设备备件库存管理、领用申请及报表统计',
    path: '/mechanical',
    iconEmoji: '⚙️',
    accentColor: '#67C23A',
  },

  // ===== 新模块模板（取消注释并填写即可启用） =====
  // {
  //   id: 'process',
  //   name: '工艺管理',
  //   description: '工艺文件、工艺流程及变更记录管理',
  //   path: '/process',
  //   iconEmoji: '📋',
  //   accentColor: '#E6A23C',
  // },
  // {
  //   id: 'safety',
  //   name: '安全管理',
  //   description: '安全检查、隐患排查及事故记录',
  //   path: '/safety',
  //   iconEmoji: '🛡️',
  //   accentColor: '#F56C6C',
  // },
]

/** 所有模块均可通过 permissions 列配置（电气/机械不再有 isLegacy 标记） */
export const NEW_MODULES = ALL_MODULES

/** 按 id 快速查找模块定义 */
export function getModuleById(id: string): ModuleDefinition | undefined {
  return ALL_MODULES.find((m) => m.id === id)
}

/**
 * 各角色可管理的模块及授权上限（与后端 MANAGED_MODULES 对应）
 * key = 角色，value = { modules: 可管理模块集合, maxLevel: 可授予最高级别 }
 */
export const ROLE_MANAGED_MODULES: Record<string, { modules: string[]; maxLevel: ModulePermLevel }> = {
  electrical_admin: { modules: ['electrical'], maxLevel: 'editor' },
  mechanical_admin: { modules: ['mechanical'], maxLevel: 'editor' },
}
