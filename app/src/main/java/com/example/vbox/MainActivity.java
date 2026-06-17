package com.example.vbox;

import androidx.appcompat.app.AppCompatActivity;
import android.os.Bundle;
import android.view.View;
import android.view.WindowInsets;
import android.view.View.OnApplyWindowInsetsListener;
import android.view.WindowInsetsController;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 设置全屏但不包含刘海区域
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_IMMERSIVE
        );

        // 设置窗口标志，确保不占用刘海区域
        getWindow().addFlags(
            android.view.WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS
            | android.view.WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        );

        // 设置内容视图
        setContentView(R.layout.activity_main);

        // 处理窗口插入
        OnApplyWindowInsetsListener listener = new OnApplyWindowInsetsListener() {
            @Override
            public WindowInsets onApplyWindowInsets(View v, WindowInsets insets) {
                // 确保内容不被刘海区域遮挡
                v.setPadding(
                    insets.getSystemWindowInsetLeft(),
                    0, // 顶部不设置内边距，避免占用刘海区域
                    insets.getSystemWindowInsetRight(),
                    insets.getSystemWindowInsetBottom()
                );

                // 如果需要，可以在这里获取刘海区域高度，用于调整UI布局
                // int notchHeight = insets.getSystemWindowInsetTop();

                return insets;
            }
        };

        getWindow().getDecorView().setOnApplyWindowInsetsListener(listener);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            // 再次确保不占用刘海区域
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE
            );

            // 对于Android 11及以上版本，使用WindowInsetsController
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.R) {
                WindowInsetsController insetsController = getWindow().getInsetsController();
                if (insetsController != null) {
                    // 隐藏状态栏但不包括刘海区域
                    insetsController.hide(android.view.WindowInsets.Type.statusBars());
                }
            }
        }
    }
}
