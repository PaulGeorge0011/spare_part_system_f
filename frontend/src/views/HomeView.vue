<template>
  <div class="home-page">
    <div class="welcome-banner">
      <div class="welcome-text">
        <p class="welcome-greeting">您好，{{ displayName }}</p>
        <p class="welcome-sub">请选择要进入的管理模块</p>
      </div>
      <div class="welcome-role">
        <el-tag :type="roleTagType" size="large">{{ roleLabel }}</el-tag>
      </div>
    </div>

    <div v-if="accessibleModules.length > 0" class="module-grid">
      <div
        v-for="mod in accessibleModules"
        :key="mod.id"
        class="module-card"
        :style="{ '--accent': mod.accentColor }"
        @click="router.push(mod.path)"
      >
        <div class="card-accent-bar" />
        <div class="card-body">
          <span class="card-icon">{{ mod.iconEmoji }}</span>
          <div class="card-info">
            <h3 class="card-name">{{ mod.name }}</h3>
            <p class="card-desc">{{ mod.description }}</p>
          </div>
        </div>
        <div class="card-footer">
          <el-button type="primary" size="small" plain>进入 →</el-button>
        </div>
      </div>
    </div>

    <el-empty
      v-else
      description="您暂无任何模块的访问权限，请联系管理员分配权限"
      :image-size="120"
      class="no-module"
    />
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'HomeView' })

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ALL_MODULES } from '@/utils/modules'
import { ROLE_LABELS } from '@/api/user'

const router = useRouter()
const authStore = useAuthStore()

const displayName = computed(
  () => authStore.user?.real_name || authStore.user?.username || '',
)

const roleLabel = computed(
  () => ROLE_LABELS[authStore.user?.role ?? ''] ?? authStore.user?.role ?? '',
)

const roleTagType = computed(() => {
  const r = authStore.user?.role ?? ''
  if (r === 'admin') return 'danger'
  if (r.endsWith('_admin')) return 'warning'
  return 'primary'
})

const accessibleModules = computed(() =>
  ALL_MODULES.filter((m) => authStore.canAccessModule(m.id)),
)
</script>

<style scoped lang="scss">
.home-page {
  padding: 24px 28px 32px;
  max-width: 960px;
  margin: 0 auto;
}

/* 欢迎横幅 */
.welcome-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #f0f7ff 0%, #f5f7fa 100%);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
}

.welcome-greeting {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: #1d2939;
}

.welcome-sub {
  margin: 0;
  font-size: 14px;
  color: #667085;
}

/* 模块卡片网格 */
.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
}

.module-card {
  position: relative;
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  flex-direction: column;

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);

    .card-footer .el-button {
      background-color: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
  }
}

.card-accent-bar {
  height: 4px;
  background: var(--accent, #409eff);
}

.card-body {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 18px 12px;
  flex: 1;
}

.card-icon {
  font-size: 36px;
  line-height: 1;
  flex-shrink: 0;
}

.card-name {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: #1d2939;
}

.card-desc {
  margin: 0;
  font-size: 13px;
  color: #667085;
  line-height: 1.5;
}

.card-footer {
  padding: 10px 18px 16px;
  display: flex;
  justify-content: flex-end;
}

.no-module {
  margin-top: 40px;
}

/* 移动端自适应 */
@media (max-width: 767px) {
  .home-page {
    padding: 16px 12px 24px;
  }

  .welcome-banner {
    padding: 14px 16px;
    margin-bottom: 20px;
  }

  .welcome-greeting {
    font-size: 16px;
  }

  .module-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }
}
</style>
