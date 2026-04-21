import { nextTick } from 'vue'

/**
 * 将主内容区（.app-main）滚动到顶部。
 * 用于移动端/桌面端：点击「查询」等按钮并关闭搜索抽屉后，自动回到列表顶部。
 * iframe 与一般网页均适用。
 */
export function scrollMainToTop() {
  nextTick(() => {
    const main = document.querySelector('.app-main')
    if (main) main.scrollTo({ top: 0, behavior: 'smooth' })
  })
}
