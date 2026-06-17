# VBox TV应用 Capacitor 构建指南

## 项目概述

本项目已从Cordova迁移到Capacitor，以提供更好的性能和开发体验。本指南将帮助您构建VBox TV应用。

## 环境要求

1. Node.js (建议 v16.x 或更高版本)
2. npm (通常随Node.js一起安装)
3. Android Studio (用于构建Android应用)
4. Java Development Kit (JDK) 11或更高版本
5. Android SDK (包含Android TV支持)

## 安装步骤

### 1. 安装依赖

```bash
npm install
```

### 2. 安装Capacitor CLI

如果尚未全局安装Capacitor CLI，请运行：

```bash
npm install -g @capacitor/cli
```

### 3. 添加Android平台

```bash
npx cap add android
```

## 构建步骤

### 1. 构建Web应用

```bash
npm run build
```

### 2. 同步到原生项目

```bash
npx cap sync
```

### 3. 打开Android项目

```bash
npx cap open android
```

### 4. 在Android Studio中构建APK

1. 等待Android Studio完成项目同步
2. 确保已选择正确的构建变体（通常为"release"）
3. 点击"Build"菜单，然后选择"Generate Signed Bundle / APK"
4. 选择"APK"
5. 点击"Next"
6. 选择"release"构建变体
7. 点击"Create"
8. 如果已有密钥库，选择"Choose existing"并指定密钥库路径和密码；如果没有密钥库，选择"Create new"并按照向导创建
9. 点击"Finish"完成签名过程

构建完成后，APK文件将保存在 `android/app/build/outputs/apk/release/` 目录中。

## 可用脚本

- `npm run build` - 构建Web应用
- `npm run android:build` - 构建Web应用并同步到Android项目
- `npm run android:run` - 构建Web应用并运行Android应用
- `npm run android:debug` - 构建Web应用并以调试模式运行Android应用
- `npm run android:release` - 构建Web应用、同步到Android项目并构建发布APK
- `npm run android:open` - 在Android Studio中打开Android项目
- `npm run sync` - 构建Web应用并同步到原生项目
- `npm run serve` - 启动开发服务器

## TV功能说明

此TV版应用已针对Android TV平台进行优化，支持：

- 电视遥控器方向键导航
- 大屏幕UI优化
- 适合远距离观看的字体大小
- TV焦点管理

## 故障排除

### 常见问题

1. **npm install失败**
   - 确保使用正确的Node.js版本
   - 尝试删除node_modules和package-lock.json，然后重新运行npm install

2. **Android Studio同步失败**
   - 确保已正确配置Android SDK路径
   - 检查Java版本是否兼容
   - 尝试"File" > "Invalidate Caches / Restart"

3. **应用无法在Android TV上运行**
   - 确保已添加Android TV支持到AndroidManifest.xml
   - 检查是否已添加leanback支持库

### 调试技巧

1. **查看日志**
   ```bash
   npm run android:debug
   ```
   然后在Android Studio中查看Logcat。

2. **使用Chrome DevTools**
   ```bash
   npm run android:debug
   ```
   然后在Chrome中访问 `chrome://inspect/#devices`。

## 下一步

1. 添加更多TV特定的功能，如语音搜索、手势控制等
2. 优化性能和用户体验
3. 添加更多平台支持（如iOS、Web）
