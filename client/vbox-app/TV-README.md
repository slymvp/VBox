# VBox TV版应用

这是VBox应用的电视版本，专为Android TV平台设计，支持使用电视遥控器进行操作。

## 功能特点

- 支持Android TV平台
- 优化了电视遥控器操作体验
- 适配大屏幕显示
- 增强的焦点导航系统
- 针对电视优化的UI布局

## 构建步骤

### 方法一：使用Android Studio构建（推荐）

项目已从Cordova迁移到Capacitor，推荐使用以下步骤构建：

1. 打开命令提示符或PowerShell
2. 进入项目目录：`cd d:\MyCodes\VBox\client\vbox-app`
3. 运行构建脚本：`build-capacitor.bat`
4. 等待脚本完成Vue应用构建和Capacitor同步
5. 脚本将自动打开Android Studio项目
6. 在Android Studio中完成最终构建和签名过程

构建完成后，APK文件将保存在 `android/app/build/outputs/apk/release/` 目录中。

### 方法二：手动构建

如果您想手动执行构建步骤：

1. **安装依赖**
   ```bash
   npm install
   ```

2. **构建Web应用**
   ```bash
   npm run build
   ```

3. **同步到原生项目**
   ```bash
   npm run sync
   ```

4. **打开Android项目**
   ```bash
   npm run android:open
   ```

5. 在Android Studio中完成最终构建和签名过程

### 可用脚本

- `npm run build` - 构建Web应用
- `npm run android:build` - 构建Web应用并同步到Android项目
- `npm run android:run` - 构建Web应用并运行Android应用
- `npm run android:debug` - 构建Web应用并以调试模式运行Android应用
- `npm run android:release` - 构建Web应用、同步到Android项目并构建发布APK
- `npm run android:open` - 在Android Studio中打开Android项目
- `npm run sync` - 构建Web应用并同步到原生项目
- `npm run serve` - 启动开发服务器

## 构建故障排除

如果遇到构建问题，请查看 `BUILD_CAPACITOR_GUIDE.md` 文件获取详细的故障排除指南。

## 遥控器操作指南

- **方向键上/下/左/右**：导航界面元素
- **确定键（Enter）**：选择或激活当前焦点元素
- **返回键**：返回上一级界面
- **菜单键**：打开上下文菜单（如果可用）

## TV界面优化

- 增大的字体和按钮尺寸，适合远距离观看
- 清晰的焦点指示器
- 优化的布局，适应不同尺寸的电视屏幕
- 流畅的动画和过渡效果

## 注意事项

1. 确保已安装Android SDK和必要的构建工具
2. 构建前请确保所有依赖已正确安装
3. 首次构建可能需要较长时间，请耐心等待

## 故障排除

如果构建过程中遇到问题，请检查：

1. Node.js和npm是否已正确安装
2. Android SDK路径是否正确配置
3. 是否有足够的磁盘空间进行构建
4. 是否有必要的权限执行构建命令

## 技术支持

如有问题，请联系开发团队或提交Issue到项目仓库。
