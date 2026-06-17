# VBox 移动端和TV端架构说明

## 📋 架构概述

本项目采用**环境变量 + 运行时检测**的组合方案，实现移动端和TV端的UI差异化：

- **构建时区分**：通过环境变量控制打包不同的UI
- **运行时适配**：通过设备检测自动适配TV/移动端
- **代码复用**：共享业务逻辑，只区分UI层

## 🎯 目录结构

```
client/
├── src/
│   ├── components/
│   │   ├── mobile/          # 移动端专用组件
│   │   │   ├── Header.vue
│   │   │   └── Sidebar.vue
│   │   ├── tv/              # TV端专用组件
│   │   │   ├── Header.vue
│   │   │   └── Sidebar.vue
│   │   └── shared/          # 共享组件
│   │       ├── Toast.vue
│   │       └── ...
│   ├── layouts/
│   │   ├── MobileLayout.vue
│   │   └── TVLayout.vue
│   ├── stores/
│   │   └── device.ts        # 设备状态管理
│   ├── utils/
│   │   └── device.ts        # 设备检测工具
│   └── App.vue              # 主应用（根据设备类型选择布局）
├── .env.mobile              # 移动端环境变量
├── .env.tv                  # TV端环境变量
└── package.json
```

## 🔧 环境变量

### 移动端配置 (.env.mobile)
```bash
VITE_PLATFORM=mobile
VITE_API_BASE=/api
VITE_APP_NAME=VBox Mobile
```

### TV端配置 (.env.tv)
```bash
VITE_PLATFORM=tv
VITE_API_BASE=/api
VITE_APP_NAME=VBox TV
```

## 🚀 构建脚本

### 使用 build-apk.bat

```cmd
build-apk.bat
```

选择要打包的版本：
- **1** - 移动端 (Mobile)
- **2** - TV端 (TV)
- **3** - 全部 (All)
- **0** - 退出

### 手动构建

```cmd
# 构建移动端
cd client
npm run build:mobile

# 构建TV端
cd client
npm run build:tv
```

## 🎨 UI差异

### 移动端特点
- **触摸交互**：点击、滑动、手势
- **小屏幕**：紧凑布局、底部导航
- **竖屏为主**：垂直滚动、卡片列表
- **字体较小**：14-16px
- **底部导航栏**：首页、搜索、VIP、我的

### TV端特点
- **遥控器交互**：方向键、确认键、返回键
- **大屏幕**：宽敞布局、侧边导航
- **横屏为主**：网格布局、焦点管理
- **字体较大**：24-28px
- **焦点样式**：明显的焦点边框（3px solid #f59e0b）
- **侧边导航栏**：平台选择、数据统计

## 📱 设备检测

### 自动检测规则

```typescript
// TV设备特征：大屏幕、支持遥控器
const isTV = width >= 1920 ||
             width >= 1360 && height >= 768 ||
             navigator.userAgent.includes('TV') ||
             navigator.userAgent.includes('Tizen') ||
             navigator.userAgent.includes('WebOS')
```

### 使用示例

```vue
<template>
  <div>
    <!-- 移动端UI -->
    <div v-if="deviceStore.isMobile">
      <MobileHeader />
      <MobileContent />
    </div>

    <!-- TV端UI -->
    <div v-else>
      <TVHeader />
      <TVContent />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDeviceStore } from '@/stores/device'

const deviceStore = useDeviceStore()
</script>
```

## 🔌 组件使用

### 在布局中使用

```vue
<!-- MobileLayout.vue -->
<template>
  <div class="mobile-layout">
    <MobileHeader />
    <main class="content">
      <slot />
    </main>
    <MobileSidebar />
  </div>
</template>

<!-- TVLayout.vue -->
<template>
  <div class="tv-layout">
    <TVHeader />
    <main class="content">
      <slot />
    </main>
    <TVSidebar />
  </div>
</template>
```

### 在页面中使用

```vue
<template>
  <div class="page">
    <!-- 根据设备类型显示不同内容 -->
    <div v-if="deviceStore.isTV" class="tv-ui">
      <TVGrid :items="items" />
    </div>
    <div v-else class="mobile-ui">
      <MobileList :items="items" />
    </div>
  </div>
</template>
```

## 📦 APK 输出

APK 文件会自动复制到桌面，文件名格式：

```
VBoxMobile-debug-YYYYMMDD.apk
VBoxTV-debug-YYYYMMDD.apk
```

## 🎯 TV遥控器焦点管理

TV端支持遥控器操作，通过 `.focusable` 类标记可聚焦元素：

```vue
<button class="focusable" @click="handleClick">
  点击我
</button>
```

焦点样式：
```scss
.focusable:focus {
  outline: 3px solid #f59e0b !important;
  outline-offset: 2px;
}
```

## 🔄 开发流程

1. **开发移动端**
   ```cmd
   cd client
   npm run dev
   ```

2. **开发TV端**
   ```cmd
   cd client
   VITE_PLATFORM=tv npm run dev
   ```

3. **构建APK**
   ```cmd
   build-apk.bat
   ```

## 📝 注意事项

1. **首次构建**：首次构建可能需要下载依赖，会比较慢
2. **组件复用**：共享组件放在 `components/shared/` 目录
3. **样式适配**：使用媒体查询适配不同屏幕尺寸
4. **TV端测试**：建议使用模拟器或真实TV设备测试遥控器操作

## 🎨 样式规范

### 移动端
- 字体：14-16px
- 间距：8-16px
- 圆角：6-8px
- 阴影：轻微阴影

### TV端
- 字体：24-28px
- 间距：16-24px
- 圆角：10-12px
- 阴影：明显阴影
- 焦点：3px边框

## 🚀 性能优化

1. **代码分割**：按需加载移动端/TV端组件
2. **图片优化**：使用不同尺寸的图片
3. **懒加载**：延迟加载非关键组件
4. **缓存策略**：合理使用浏览器缓存

## 📱 测试建议

### 移动端测试
- iPhone SE (375x667)
- iPhone 12 Pro (390x844)
- Android (360x640)

### TV端测试
- 1080p (1920x1080)
- 4K (3840x2160)
- 模拟器测试遥控器操作

## 🔍 调试

### 查看设备信息

```javascript
import { useDeviceStore } from '@/stores/device'

const deviceStore = useDeviceStore()
console.log('Platform:', deviceStore.platform)
console.log('Device Type:', deviceStore.deviceType)
console.log('Is TV:', deviceStore.isTV)
console.log('Is Mobile:', deviceStore.isMobile)
```

### 强制切换设备类型

在控制台运行：

```javascript
// 强制切换到TV模式
localStorage.setItem('vbox_platform', 'tv')
location.reload()

// 强制切换到移动端模式
localStorage.setItem('vbox_platform', 'mobile')
location.reload()
```

## 📚 相关文档

- [Vite 官方文档](https://vitejs.dev/)
- [Vue 3 官方文档](https://vuejs.org/)
- [Capacitor 官方文档](https://capacitorjs.com/)
- [TV开发最佳实践](https://developer.android.com/training/tv)

---

**版本**: 1.0.0
**更新日期**: 2026-06-11
**维护者**: VBox Team