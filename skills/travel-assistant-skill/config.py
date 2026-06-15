"""旅伴  配置"""
import os

# ── 高德地图 ──
_env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.amap")
_amap_env = {}
if os.path.isfile(_env_file):
    for line in open(_env_file, encoding="latin-1"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            _amap_env[k.strip()] = v.strip()

AMAP_JSAPI_KEY = _amap_env.get("AMAP_JSAPI_KEY", "")
AMAP_JSAPI_SECURITY_CODE = _amap_env.get("AMAP_JSAPI_SECURITY_CODE", "")
AMAP_WEBSERVICE_KEY = _amap_env.get("AMAP_WEBSERVICE_KEY", "")
AMAP_KEY = _amap_env.get("AMAP_KEY", "")

# ── 小红书 ──
XHS_SCRIPT = os.environ.get("XHS_SCRIPT", "/path/to/xiaohongshu-mcp.sh")
XHS_COOKIES = os.environ.get("XHS_COOKIES", "/path/to/cookies.json")
XHS_TIMEOUT = 60

# ── 飞猪 ──
FLYAI_CMD = os.environ.get("FLYAI_CMD", "flyai")
FLYAI_TIMEOUT = 70

# ── 模型 ──
MODEL_NAME = os.environ.get("MODEL_NAME", "qwen3-30b-a3b")
MAAS_API_KEY = os.environ.get("MAAS_API_KEY", "")
MAAS_API_URL = os.environ.get("MAAS_API_URL", "")

# ── 路径 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outs")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
POI_CACHE_DIR = os.path.join(BASE_DIR, "data", "poi_cache")

# ── 规划参数 ──
MAX_ATTRACTIONS_PER_DAY = 5
MAX_HOURS_PER_DAY = 10
DEFAULT_START_HOUR = 9
DEFAULT_END_HOUR = 21

# ── 高德并发 ──
AMAP_MIN_INTERVAL = 1.2  # 秒
AMAP_CONCURRENT_LIMIT = 3
