<template>
  <div class="spare-part-images">
    <!-- 表格专用紧凑布局 -->
    <div v-if="hasImages" class="compact-images">
      <div 
        v-for="(image, index) in imageList" 
        :key="index"
        class="compact-image-item"
      >
        <el-image 
          :src="getOptimizedUrl(image.url)" 
          :alt="image.alt || `图片 ${index + 1}`"
          fit="cover"
          :preview-src-list="previewList"
          :initial-index="index"
          :zoom-rate="1.2"
          :max-scale="7"
          :min-scale="0.2"
          preview-teleported
          :hide-on-click-modal="true"
          class="table-image"
        >
          <template #error>
            <div class="image-error">
              <i class="el-icon-picture-outline"></i>
              <p>加载失败</p>
            </div>
          </template>
          
          <template #placeholder>
            <div class="image-loading">
              <i class="el-icon-loading"></i>
              <p>加载中</p>
            </div>
          </template>
        </el-image>
        
        <!-- 只在有多个图片时显示标签 -->
        <div v-if="imageList.length > 1" class="compact-image-label">
          {{ index === 0 ? '图1' : '图2' }}
        </div>
      </div>
    </div>
    
    <div v-else class="no-images-compact">
      <i class="el-icon-picture-outline"></i>
      <p>无图片</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getImageUrl } from '@/utils/imageUpload'
import { getImageUrlForDisplay } from '@/utils/image'

interface Props {
  images: string[]  // 图片URL数组
  editable?: boolean
  sparePartId?: number
  showHeader?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  images: () => [],
  editable: false,
  showHeader: true
})

const emit = defineEmits<{
  'edit': []
  'remove': [index: number]
}>()

// 计算属性
const hasImages = computed(() => {
  return props.images.some(url => url && url.trim() !== '')
})

const imageList = computed(() => {
  return props.images
    .filter(url => url && url.trim() !== '')
    .map((url, index) => ({
      url,
      alt: `修复件图片 ${index + 1}`
    }))
})

const previewList = computed(() => {
  return imageList.value.map(img => getOptimizedUrl(img.url, { width: 800 }))
})

// 获取优化后的图片URL（用于显示和预览，移动端 localhost 需转当前 host）
const getOptimizedUrl = (url: string, options = { width: 120, quality: 80 }) => {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return getImageUrlForDisplay(url)
  }
  
  // 如果是以 /api/v1/ 开头的路径，直接拼接基础URL（不重复添加）
  if (url.startsWith('/api/v1/')) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    // 注意：baseUrl 已经是 http://localhost:8000/api/v1
    // 所以我们需要从 url 中去掉开头的 /api/v1 再拼接
    const pathWithoutPrefix = url.startsWith('/api/v1') ? url.substring(7) : url
    return `${baseUrl}${pathWithoutPrefix}`
  }
  
  // 如果是以 /images/ 开头的相对路径
  if (url.startsWith('/images/')) {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    return `${baseUrl}${url}`
  }
  
  // 其他情况，尝试使用 getImageUrl 函数处理
  try {
    return getImageUrl(url, options)
  } catch {
    // 如果 getImageUrl 处理失败，尝试直接返回
    const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    return `${baseUrl}${url.startsWith('/') ? '' : '/'}${url}`
  }
}
</script>

<style scoped lang="scss">
.spare-part-images {
  width: 100%;
  height: 100%;
}

.compact-images {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.compact-image-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  position: relative;
}

.table-image {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s ease;
  border: 1px solid #ebeef5;
  
  &:hover {
    transform: scale(1.05);
    border-color: #409eff;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
  }
}

.compact-image-label {
  font-size: 10px;
  color: #909399;
  background: #f5f7fa;
  padding: 1px 4px;
  border-radius: 2px;
  line-height: 1.2;
}

.image-error,
.image-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  width: 100%;
  color: #909399;
  background: #f5f7fa;
  border-radius: 4px;
  
  i {
    font-size: 16px;
    margin-bottom: 2px;
  }
  
  p {
    margin: 0;
    font-size: 10px;
    text-align: center;
  }
}

.image-loading {
  i {
    animation: rotating 2s linear infinite;
  }
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.no-images-compact {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  
  i {
    font-size: 20px;
    margin-bottom: 4px;
  }
  
  p {
    margin: 0;
    font-size: 10px;
    text-align: center;
  }
}
</style>