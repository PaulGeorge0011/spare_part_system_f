import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

// iframe + 移动端：内容按 375px 布局，再用 zoom 整体放大到视觉视口宽度，避免需手动放大且领用等页面显示正常
const IFRAME_MOBILE_CONTENT_WIDTH = 375
if (typeof window !== 'undefined') {
  try {
    const inIframe = window.self !== window.top
    const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile/i.test(navigator.userAgent || '')
    if (inIframe && isMobileUA) {
      document.documentElement.classList.add('iframe-mobile-viewport')
      const w = `${IFRAME_MOBILE_CONTENT_WIDTH}px`

      const updateZoom = () => {
        const vw = window.visualViewport?.width ?? window.innerWidth
        const zoom = Math.max(0.5, Math.min(2.5, vw / IFRAME_MOBILE_CONTENT_WIDTH))
        document.documentElement.style.setProperty('--iframe-mobile-zoom', String(zoom))
      }
      updateZoom()
      window.visualViewport?.addEventListener('resize', updateZoom)
      window.addEventListener('orientationchange', updateZoom)

      const style = document.createElement('style')
      style.id = 'iframe-mobile-viewport-style'
      style.textContent = [
        'html.iframe-mobile-viewport, html.iframe-mobile-viewport body { margin: 0 !important; overflow-x: hidden !important; box-sizing: border-box !important; height: 100% !important; }',
        `#iframe-mobile-scaler { width: ${w} !important; min-width: ${w} !important; max-width: ${w} !important; height: 100% !important; min-height: 100% !important; zoom: var(--iframe-mobile-zoom, 1) !important; transform-origin: top left !important; box-sizing: border-box !important; display: flex !important; flex-direction: column !important; }`,
        '#iframe-mobile-scaler #app { width: 100% !important; box-sizing: border-box !important; height: 100% !important; min-height: 0 !important; display: flex !important; flex-direction: column !important; overflow: hidden !important; }',
        'html.iframe-mobile-viewport #app:not(.app-logged-in) { overflow-x: hidden !important; overflow-y: auto !important; -webkit-overflow-scrolling: touch !important; }',
        'html.iframe-mobile-viewport #app:not(.app-logged-in) > * { flex: none !important; min-height: min-content !important; }',
        'html.iframe-mobile-viewport #app:not(.app-logged-in) .login-page { overflow: visible !important; min-height: 100% !important; align-items: flex-start !important; justify-content: flex-start !important; padding: 20px 12px 40px !important; box-sizing: border-box !important; }',
        'html.iframe-mobile-viewport #app:not(.app-logged-in) .register-page { min-height: auto !important; padding: 20px 12px 32px !important; box-sizing: border-box !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog { display: flex !important; flex-direction: column !important; width: 100% !important; max-width: 100% !important; max-height: 85vh !important; margin: 0 !important; box-sizing: border-box !important; min-width: 0 !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog__header { flex-shrink: 0 !important; padding: 14px 16px !important; min-width: 0 !important; position: relative !important; z-index: 2 !important; pointer-events: auto !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog__body { flex: 1 !important; min-height: 0 !important; min-width: 0 !important; max-width: 100% !important; overflow-x: hidden !important; overflow-y: auto !important; -webkit-overflow-scrolling: touch !important; padding: 12px 16px !important; box-sizing: border-box !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog__body .el-form { min-width: 0 !important; max-width: 100% !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog__body .el-form-item { min-width: 0 !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog__body .el-input { max-width: 100% !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) .el-dialog__footer { flex-shrink: 0 !important; padding: 12px 16px !important; min-width: 0 !important; position: relative !important; z-index: 2 !important; pointer-events: auto !important; }',
        'html.iframe-mobile-viewport #app.app-logged-in .app-container { flex: 1 !important; min-height: 0 !important; display: flex !important; flex-direction: column !important; overflow: hidden !important; }',
        'html.iframe-mobile-viewport #app.app-logged-in .app-container .el-header { height: 56px !important; min-height: 56px !important; max-height: 56px !important; flex-shrink: 0 !important; padding: 0 12px !important; display: flex !important; align-items: center !important; }',
        'html.iframe-mobile-viewport #app.app-logged-in .app-container .el-header .header-content { height: 56px !important; min-height: 56px !important; }',
        'html.iframe-mobile-viewport #app.app-logged-in .app-container .el-main { flex: 1 !important; min-height: 0 !important; overflow: auto !important; -webkit-overflow-scrolling: touch !important; }',
        'html.iframe-mobile-viewport .el-overlay { zoom: var(--iframe-mobile-zoom, 1) !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-drawer:not(.mobile-search-drawer-unified)) { zoom: 1 !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-drawer:not(.mobile-search-drawer-unified)) .el-drawer { max-width: 85vw !important; box-sizing: border-box !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-drawer.mobile-search-drawer-unified) { zoom: 1 !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) { zoom: 1 !important; display: flex !important; align-items: center !important; justify-content: center !important; padding: 0 12px !important; box-sizing: border-box !important; width: 100% !important; max-width: 100% !important; overflow-x: hidden !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-dialog) > div { max-width: 100% !important; min-width: 0 !important; }',
        'html.iframe-mobile-viewport .el-overlay:has(.el-message-box) { zoom: 1 !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .el-drawer__body { font-size: 15px !important; line-height: 1.5 !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .el-input__inner { font-size: 16px !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .el-input input { font-size: 16px !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .el-select .el-select__input { font-size: 16px !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .el-select .el-select__placeholder { font-size: 16px !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .filter-group { margin-bottom: 20px !important; gap: 8px !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .filter-label { font-size: 15px !important; font-weight: 600 !important; color: #334155 !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .filter-actions { margin-top: 24px !important; padding-top: 20px !important; }',
        'html.iframe-mobile-viewport .mobile-search-drawer-unified .el-button { font-size: 15px !important; min-height: 44px !important; border-radius: 10px !important; }',
        'html.iframe-mobile-viewport .el-message { zoom: var(--iframe-mobile-zoom, 1) !important; }',
        'html.iframe-mobile-viewport .el-notification { zoom: var(--iframe-mobile-zoom, 1) !important; }',
        'html.iframe-mobile-viewport .table-card .el-card__body { overflow: visible !important; }',
        'html.iframe-mobile-viewport .card-list-wrap { margin-bottom: 16px !important; padding: 0 2px !important; }',
        'html.iframe-mobile-viewport .card-list { display: flex !important; flex-direction: column !important; gap: 14px !important; }',
        'html.iframe-mobile-viewport .req-card { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important; border-radius: 14px !important; padding: 20px !important; border: 1px solid rgba(0,0,0,0.06) !important; border-left: 4px solid var(--el-color-success) !important; box-shadow: 0 4px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04) !important; transition: transform 0.2s ease, box-shadow 0.2s ease !important; display: flex !important; flex-direction: column !important; gap: 12px !important; transform: translateZ(0) !important; backface-visibility: hidden !important; }',
        'html.iframe-mobile-viewport .req-card:active { transform: translateZ(0) scale(0.99) !important; }',
        'html.iframe-mobile-viewport .req-card.req-card-zero { border-left-color: var(--el-color-danger) !important; background: linear-gradient(to bottom, #fef2f2, #fee2e2) !important; }',
        'html.iframe-mobile-viewport .req-card.req-card-low { border-left-color: var(--el-color-warning) !important; background: linear-gradient(to bottom, #fffbeb, #fef3c7) !important; }',
        'html.iframe-mobile-viewport .req-card-btn { width: 100% !important; font-weight: 600 !important; font-size: 15px !important; padding: 12px 16px !important; border-radius: 10px !important; position: relative !important; z-index: 1 !important; min-height: 44px !important; -webkit-tap-highlight-color: transparent !important; box-sizing: border-box !important; }',
        'html.iframe-mobile-viewport .req-card-row { display: flex !important; align-items: center !important; gap: 8px !important; margin-bottom: 0 !important; }',
        'html.iframe-mobile-viewport .req-code { font-family: "SF Mono", Monaco, "Courier New", monospace !important; font-size: 14px !important; color: #409eff !important; font-weight: 600 !important; }',
        'html.iframe-mobile-viewport .req-card-desc { font-size: 15px !important; color: #334155 !important; line-height: 1.5 !important; margin-bottom: 0 !important; }',
        'html.iframe-mobile-viewport .req-card-location { font-size: 13px !important; color: #67c23a !important; display: flex !important; align-items: center !important; gap: 4px !important; margin-bottom: 0 !important; }',
        'html.iframe-mobile-viewport .req-card-meta { display: flex !important; flex-wrap: wrap !important; gap: 6px !important; margin-bottom: 0 !important; }',
        'html.iframe-mobile-viewport .req-card-stock { font-size: 13px !important; color: #64748b !important; margin-bottom: 0 !important; }',
        'html.iframe-mobile-viewport .req-card-images .el-image { border-radius: 6px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; }',
        'html.iframe-mobile-viewport .req-drawing { font-size: 12px !important; color: var(--el-text-color-secondary) !important; }',
        'html.iframe-mobile-viewport .req-card-physical-image-row { display: flex !important; align-items: center !important; gap: 8px !important; }',
        'html.iframe-mobile-viewport .req-card-physical-image-label { font-size: 12px !important; color: var(--el-text-color-secondary) !important; flex-shrink: 0 !important; width: 72px !important; }',
        'html.iframe-mobile-viewport .req-card-physical-image { width: 48px !important; height: 48px !important; border-radius: 6px !important; overflow: hidden !important; flex-shrink: 0 !important; }',
        'html.iframe-mobile-viewport .load-more-sentinel { min-height: 48px !important; display: flex !important; align-items: center !important; justify-content: center !important; padding: 16px !important; font-size: 13px !important; color: #909399 !important; }',
        'html.iframe-mobile-viewport .mobile-total-tip { text-align: center !important; padding: 12px 16px !important; font-size: 13px !important; color: #64748b !important; font-weight: 500 !important; background: linear-gradient(to bottom, #f8fafc, #fff) !important; border-radius: 8px !important; margin-top: 12px !important; }',
        'html.iframe-mobile-viewport .reports-page .chart-container { height: calc(260px * var(--iframe-mobile-zoom, 1)) !important; min-height: calc(260px * var(--iframe-mobile-zoom, 1)) !important; zoom: calc(1 / var(--iframe-mobile-zoom, 1)) !important; transform-origin: top center !important; }'
      ].join(' ')
      document.head.appendChild(style)
    }
  } catch {
    // 跨域等无法访问 window.top 时忽略
  }
}

// Element Plus 样式（按需导入组件，但样式仍需导入）
import 'element-plus/dist/index.css'


// 只注册常用图标，其他图标在组件中按需导入
import {
  Menu,
  Search,
  Plus,
  Edit,
  Delete,
  Refresh,
  Download,
  Upload,
  ArrowLeft,
  ArrowRight,
  Close,
  Check,
  Warning,
  InfoFilled,
  SuccessFilled,
  CircleCloseFilled,
  Loading,
  User,
  Lock,
  View,
  Hide,
  Setting,
  Document,
  Folder,
  Picture,
  Calendar,
  Clock,
  Location,
  Phone,
  Message,
  Star,
  StarFilled,
  Filter,
  Sort,
  More,
  MoreFilled,
  Operation,
  Tickets,
  List,
  Grid,
  Histogram,
  TrendCharts,
  DataAnalysis,
  PieChart,
  Goods,
  ShoppingCart,
  Box,
  Coin,
  Money,
  Files,
  FolderOpened,
  DocumentCopy,
  Printer,
  Connection,
  Share,
  SwitchButton,
  CirclePlus,
  Remove,
  ZoomIn,
  ZoomOut,
  FullScreen,
  Aim,
  Position,
  ChatDotSquare,
  ChatLineSquare,
} from '@element-plus/icons-vue'

const app = createApp(App)

// 注册常用图标
const icons = {
  Menu, Search, Plus, Edit, Delete, Refresh, Download, Upload,
  ArrowLeft, ArrowRight, Close, Check, Warning, InfoFilled,
  SuccessFilled, CircleCloseFilled, Loading, User, Lock, View, Hide,
  Setting, Document, Folder, Picture, Calendar, Clock, Location,
  Phone, Message, Star, StarFilled, Filter, Sort, More, MoreFilled,
  Operation, Tickets, List, Grid, Histogram, TrendCharts, DataAnalysis,
  PieChart, Goods, ShoppingCart, Box, Coin, Money, Files, FolderOpened,
  DocumentCopy, Printer, Connection, Share, SwitchButton, CirclePlus,
  Remove, ZoomIn, ZoomOut, FullScreen, Aim, Position, ChatDotSquare,
  ChatLineSquare,
}

for (const [key, component] of Object.entries(icons)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)

// 等待路由准备好后再挂载应用，确保首次导航正确
router.isReady().then(() => {
  app.mount('#app')
})