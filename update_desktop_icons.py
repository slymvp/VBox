from PIL import Image
import os

# 用户提供的新源图片路径
source_path = r'C:\Users\Administrator\Desktop\vbox_log2.png'

# 目标目录
public_dir = r'd:\MyCodes\VBox\client\public'
dist_dir = r'd:\MyCodes\VBox\client\dist'
vbox_app_dist_dir = r'd:\MyCodes\VBox\client\vbox-app\dist'

# Android应用图标目录
android_base_dir = r'd:\MyCodes\VBox\client\vbox-app\android\app\src\main\res'

# 安全区域比例（避免被圆角裁剪）
SAFE_ZONE = 1

# Android图标尺寸
android_sizes = {
    'mipmap-mdpi': (48, 48),
    'mipmap-hdpi': (72, 72),
    'mipmap-xhdpi': (96, 96),
    'mipmap-xxhdpi': (144, 144),
    'mipmap-xxxhdpi': (192, 192),
}

# 启动画面尺寸
splash_sizes = {
    'drawable': (512, 512),
    'drawable-land-hdpi': (800, 480),
    'drawable-land-mdpi': (480, 320),
    'drawable-land-xhdpi': (1280, 720),
    'drawable-land-xxhdpi': (1920, 1080),
    'drawable-land-xxxhdpi': (2560, 1440),
    'drawable-port-hdpi': (480, 800),
    'drawable-port-mdpi': (320, 480),
    'drawable-port-xhdpi': (720, 1280),
    'drawable-port-xxhdpi': (1080, 1920),
    'drawable-port-xxxhdpi': (1440, 2560),
}

def generate_icon(source_img, size, safe_zone=1.0):
    """生成指定尺寸的图标"""
    if safe_zone < 1.0:
        target_size = (int(size[0] * safe_zone), int(size[1] * safe_zone))
    else:
        target_size = size

    img = source_img.copy()
    img.thumbnail(target_size, Image.Resampling.LANCZOS)

    # 创建透明背景
    new_img = Image.new('RGBA', size, (0, 0, 0, 0))
    offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
    new_img.paste(img, offset)

    return new_img

try:
    # 打开源图片
    source_img = Image.open(source_path)
    print(f'源图片尺寸: {source_img.size}')

    # ========== 1. Favicon图标 ==========
    print('\n--- 生成Favicon图标 ---')

    favicon_sizes = [(16, 16), (32, 32), (48, 48), (128, 128), (256, 256)]
    favicon_images = []

    for size in favicon_sizes:
        img = generate_icon(source_img, size)
        filename = f'favicon-{size[0]}.png' if size[0] != 32 else 'favicon.png'
        img.save(os.path.join(public_dir, filename), 'PNG')
        favicon_images.append(img)

    # 生成ICO格式
    ico_path = os.path.join(public_dir, 'favicon.ico')
    favicon_images[0].save(ico_path, format='ICO', append_images=favicon_images[1:],
                          sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # 同步到dist
    for size in favicon_sizes:
        filename = f'favicon-{size[0]}.png' if size[0] != 32 else 'favicon.png'
        Image.open(os.path.join(public_dir, filename)).save(os.path.join(dist_dir, filename))
    Image.open(ico_path).save(os.path.join(dist_dir, 'favicon.ico'))

    print(f'✅ Favicon图标生成完成')

    # ========== 2. Android应用图标 ==========
    print('\n--- 生成Android应用图标 ---')

    for density, size in android_sizes.items():
        density_dir = os.path.join(android_base_dir, density)

        if not os.path.exists(density_dir):
            continue

        img = generate_icon(source_img, size, SAFE_ZONE)

        # ic_launcher.png
        img.save(os.path.join(density_dir, 'ic_launcher.png'), 'PNG')
        # ic_launcher_round.png
        img.save(os.path.join(density_dir, 'ic_launcher_round.png'), 'PNG')
        # ic_launcher_foreground.png
        img.save(os.path.join(density_dir, 'ic_launcher_foreground.png'), 'PNG')

        print(f'  {density}: {size[0]}x{size[1]}')

    print(f'✅ Android应用图标生成完成')

    # ========== 3. Android启动画面 ==========
    print('\n--- 生成Android启动画面 ---')

    for drawable, size in splash_sizes.items():
        drawable_dir = os.path.join(android_base_dir, drawable)

        if not os.path.exists(drawable_dir):
            continue

        img = generate_icon(source_img, size)
        img.save(os.path.join(drawable_dir, 'splash.png'), 'PNG')
        print(f'  {drawable}: {size[0]}x{size[1]}')

    print(f'✅ Android启动画面生成完成')

    print('\n' + '='*50)
    print('✅ 所有图标重新生成完成！')
    print('='*50)

except Exception as e:
    print(f'❌ 错误: {e}')
    import traceback
    traceback.print_exc()
