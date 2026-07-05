"""
反爬工具模块 — UA 池、请求头生成、随机延迟、代理池管理

使用方式:
    from core.anti_crawl import (
        get_random_ua,
        build_headers,
        random_delay,
        get_proxy,
        release_proxy,
        build_playwright_context_options,
        get_stealth_scripts,
    )
"""
import random
import os
import json
import time
import logging
import threading

logger = logging.getLogger('vbox.anti_crawl')

# ============================================================
# UA 池 — 10+ 真实浏览器 UA，覆盖 Chrome / Edge / Firefox / Safari
# ============================================================

USER_AGENTS = [
    # Chrome — Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    # Chrome — macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    # Edge — Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    # Firefox — Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
    # Firefox — macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:131.0) Gecko/20100101 Firefox/131.0',
    # Safari — macOS
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
]

# 对应 sec-ch-ua 的平台标识（用于构建完整请求头）
# 格式: (ua_string, sec_ch_ua, sec_ch_ua_platform, sec_ch_ua_mobile)
_UA_META = {
    'Chrome/131.0.0.0 Safari/537.36': (
        '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
        '"Windows"',
        '?0',
    ),
    'Chrome/130.0.0.0 Safari/537.36': (
        '"Chromium";v="130", "Not_A Brand";v="24", "Google Chrome";v="130"',
        '"Windows"',
        '?0',
    ),
    'Chrome/129.0.0.0 Safari/537.36': (
        '"Chromium";v="129", "Not_A Brand";v="24", "Google Chrome";v="129"',
        '"Windows"',
        '?0',
    ),
    'Chrome/128.0.0.0 Safari/537.36': (
        '"Chromium";v="128", "Not_A Brand";v="24", "Google Chrome";v="128"',
        '"Windows"',
        '?0',
    ),
    'Edg/131.0.0.0': (
        '"Chromium";v="131", "Not_A Brand";v="24", "Microsoft Edge";v="131"',
        '"Windows"',
        '?0',
    ),
    'Edg/130.0.0.0': (
        '"Chromium";v="130", "Not_A Brand";v="24", "Microsoft Edge";v="130"',
        '"Windows"',
        '?0',
    ),
    'Firefox/131.0': ('', '"Windows"', '?0'),
    'Firefox/130.0': ('', '"Windows"', '?0'),
}

# Accept-Language 池
_ACCEPT_LANGUAGES = [
    'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'zh-CN,zh;q=0.9,en;q=0.8',
    'zh-CN,zh;q=0.9',
    'zh-CN,zh;q=0.9,en-US;q=0.6,en;q=0.5',
]


def get_random_ua() -> str:
    """随机返回一个 User-Agent 字符串"""
    return random.choice(USER_AGENTS)


def _get_ua_meta(ua: str):
    """根据 UA 字符串查找对应的 sec-ch-ua 元数据"""
    for key, meta in _UA_META.items():
        if key in ua:
            return meta
    # 默认值
    return ('"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
            '"Windows"', '?0')


def build_headers(
    referer: str = '',
    origin: str = '',
    accept: str = '',
    content_type: str = '',
    ua: str = '',
    extra: dict = None,
) -> dict:
    """
    构建完整的浏览器请求头，包含 sec-ch-ua / sec-fetch-* 等现代浏览器标准头。

    :param referer: Referer URL
    :param origin: Origin URL
    :param accept: Accept 值（默认自动选择）
    :param content_type: Content-Type（POST 请求时设置）
    :param ua: 指定 UA（不传则随机）
    :param extra: 额外头，会覆盖默认值
    :return: 完整的 headers dict
    """
    if not ua:
        ua = get_random_ua()
    sec_ch_ua, sec_ch_ua_platform, sec_ch_ua_mobile = _get_ua_meta(ua)

    # 自动选择 Accept
    if not accept:
        if content_type and 'json' in content_type:
            accept = 'application/json, text/plain, */*'
        else:
            accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'

    headers = {
        'User-Agent': ua,
        'Accept': accept,
        'Accept-Language': random.choice(_ACCEPT_LANGUAGES),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # sec-ch-ua 系列（Chrome/Edge 才有，Firefox 不发）
    if sec_ch_ua:
        headers['sec-ch-ua'] = sec_ch_ua
        headers['sec-ch-ua-mobile'] = sec_ch_ua_mobile
        headers['sec-ch-ua-platform'] = sec_ch_ua_platform

    # sec-fetch 系列
    headers['Sec-Fetch-Dest'] = 'document'
    headers['Sec-Fetch-Mode'] = 'navigate'
    headers['Sec-Fetch-Site'] = 'none' if not referer else 'same-origin'
    headers['Sec-Fetch-User'] = '?1'

    if referer:
        headers['Referer'] = referer
    if origin:
        headers['Origin'] = origin
    if content_type:
        headers['Content-Type'] = content_type

    if extra:
        headers.update(extra)

    return headers


def random_delay(min_sec: float = 0.5, max_sec: float = 2.0):
    """
    随机延迟，替代固定 sleep。
    默认 0.5~2.0 秒，模拟人类操作间隔。
    """
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay


class RateLimiter:
    """
    令牌桶限速器，按平台隔离。
    用法:
        limiter = RateLimiter(qps=5)   # 每秒最多5个请求
        limiter.acquire()               # 阻塞等待令牌
    """
    _instances: dict = {}
    _lock = threading.Lock() if 'threading' in dir() else None

    def __init__(self, qps: float = 5.0, burst: int = 1):
        self.qps = qps
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    @classmethod
    def get(cls, platform: str, qps: float = 5.0) -> 'RateLimiter':
        """获取平台级限速器单例"""
        if cls._lock is None:
            import threading
            cls._lock = threading.Lock()
        with cls._lock:
            if platform not in cls._instances:
                cls._instances[platform] = cls(qps=qps)
            return cls._instances[platform]

    def acquire(self):
        """获取一个令牌，必要时阻塞等待"""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.burst, self._tokens + elapsed * self.qps)
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return  # 立即放行

            # 需要等待
            wait_time = (1.0 - self._tokens) / self.qps

        time.sleep(wait_time)
        with self._lock:
            self._tokens = max(0, self._tokens - 1.0)
            self._last_refill = time.monotonic()


def rate_limited(platform: str, qps: float = 5.0):
    """获取平台限速令牌（阻塞）"""
    RateLimiter.get(platform, qps).acquire()


# ============================================================
# 代理 IP 池 — 从环境变量或配置文件加载，轮换使用
# ============================================================

# 代理列表格式: ["http://ip:port", "http://user:pass@ip:port", ...]
# 配置方式:
#   1. 环境变量 VBOX_PROXY_LIST='["http://1.2.3.4:8080","http://5.6.7.8:3128"]'
#   2. 配置文件 server/core/proxy_list.json (JSON 数组)
_proxy_pool: list = []
_proxy_index: int = 0
_proxy_stats: dict = {}  # {proxy_url: {success: N, fail: N}}
_proxy_enabled: bool = False


def _load_proxy_pool():
    """从环境变量或配置文件加载代理池"""
    global _proxy_pool, _proxy_enabled

    # 1. 环境变量
    env_proxies = os.environ.get('VBOX_PROXY_LIST', '')
    if env_proxies:
        try:
            _proxy_pool = json.loads(env_proxies)
            logger.info(f"[代理池] 从环境变量加载了 {len(_proxy_pool)} 个代理")
        except json.JSONDecodeError:
            logger.warning("[代理池] 环境变量 VBOX_PROXY_LIST 格式错误，应为 JSON 数组")

    # 2. 配置文件
    if not _proxy_pool:
        config_path = os.path.join(os.path.dirname(__file__), 'proxy_list.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    _proxy_pool = json.load(f)
                logger.info(f"[代理池] 从配置文件加载了 {len(_proxy_pool)} 个代理")
            except Exception as e:
                logger.warning(f"[代理池] 配置文件加载失败: {e}")

    _proxy_enabled = len(_proxy_pool) > 0
    if _proxy_enabled:
        for p in _proxy_pool:
            _proxy_stats[p] = {'success': 0, 'fail': 0}


def get_proxy() -> dict:
    """
    获取一个代理，返回 requests/httpx 格式的 proxies dict。
    如果代理池为空，返回空 dict（直连）。

    使用轮换策略：按顺序取，失败多的代理降低权重。
    """
    global _proxy_index
    if not _proxy_pool:
        return {}

    # 轮换取下一个
    proxy = _proxy_pool[_proxy_index % len(_proxy_pool)]
    _proxy_index += 1
    return {'http': proxy, 'https': proxy}


def release_proxy(proxy_url: str, success: bool):
    """记录代理使用结果，用于后续权重调整"""
    if proxy_url in _proxy_stats:
        if success:
            _proxy_stats[proxy_url]['success'] += 1
        else:
            _proxy_stats[proxy_url]['fail'] += 1
            # 失败超过 5 次，移除该代理
            if _proxy_stats[proxy_url]['fail'] > 5 and _proxy_stats[proxy_url]['success'] == 0:
                logger.warning(f"[代理池] 移除失效代理: {proxy_url}")
                _proxy_pool.remove(proxy_url)
                del _proxy_stats[proxy_url]


def is_proxy_enabled() -> bool:
    """代理池是否启用"""
    return _proxy_enabled


# 启动时加载代理池
_load_proxy_pool()


# ============================================================
# 带代理轮换的 requests Session 封装
# ============================================================

class ProxySession:
    """
    带自动代理轮换的 requests.Session 封装。
    代理池为空时自动退化为直连，无需调用方关心。

    用法:
        session = ProxySession()
        resp = session.get(url, timeout=10)
    """

    def __init__(self, max_failures=5):
        import requests as _req
        self._session = _req.Session()
        self._max_failures = max_failures

    @property
    def headers(self):
        return self._session.headers

    @headers.setter
    def headers(self, value):
        self._session.headers = value

    def _do_request(self, method, url, **kwargs):
        """带代理轮换 + 失败自动重试的请求"""
        proxy_dict = get_proxy()
        proxy_url = (proxy_dict.get('http') or proxy_dict.get('https') or '') if proxy_dict else ''
        try:
            resp = self._session.request(method, url, proxies=proxy_dict or None, **kwargs)
            if proxy_url:
                release_proxy(proxy_url, True)
            return resp
        except Exception:
            if proxy_url:
                release_proxy(proxy_url, False)
            raise

    def get(self, url, **kwargs):
        return self._do_request('GET', url, **kwargs)

    def post(self, url, **kwargs):
        return self._do_request('POST', url, **kwargs)

    def head(self, url, **kwargs):
        return self._do_request('HEAD', url, **kwargs)

    def request(self, method, url, **kwargs):
        return self._do_request(method, url, **kwargs)


# ============================================================
# Playwright 上下文配置 — 随机 UA / viewport / locale
# ============================================================

# 常见 viewport 分辨率
_VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1536, 'height': 864},
    {'width': 1440, 'height': 900},
    {'width': 1366, 'height': 768},
    {'width': 1280, 'height': 720},
]

_LOCALES = ['zh-CN', 'zh-CN', 'zh-CN', 'zh-TW', 'en-US']  # 中文为主


def build_playwright_context_options(ua: str = '') -> dict:
    """
    构建 Playwright browser.new_context() 的参数，包含随机 UA / viewport / locale。

    :param ua: 指定 UA（不传则随机）
    :return: context options dict
    """
    if not ua:
        ua = get_random_ua()
    return {
        'user_agent': ua,
        'viewport': random.choice(_VIEWPORTS),
        'locale': random.choice(_LOCALES),
        'timezone_id': 'Asia/Shanghai',
        'ignore_https_errors': True,
    }


def get_stealth_scripts() -> str:
    """
    返回 Playwright 反检测注入脚本。
    覆盖 webdriver / plugins / languages / webgl / chrome 等指纹。
    """
    return """
// 隐藏 webdriver 标记
Object.defineProperty(navigator, 'webdriver', { get: () => false });

// 伪装 chrome 对象
window.chrome = {
    runtime: {},
    loadTimes: function() { return {}; },
    csi: function() { return {}; },
    app: {},
};

// 伪装 plugins（空数组是 headless 特征，模拟真实浏览器有插件）
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Microsoft Edge PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'WebKit built-in PDF', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        ];
        plugins.length = 5;
        return plugins;
    }
});

// 伪装 languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en']
});

// 伪装 permissions API
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
}

// 伪装 WebGL 指纹
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
    }
    if (parameter === 37446) {
        return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
    }
    return getParameter.call(this, parameter);
};

// 伪装 hardwareConcurrency（CPU 核心数）
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8
});

// 伪装 deviceMemory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8
});

// 伪装 platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32'
});

// 移除 Playwright/自动化相关痕迹
delete window.__playwright__script;
delete window.__pwInitScripts;
"""
