"""飞猪 CLI 客户端封装"""
import subprocess
import os
import time
from config import FLYAI_CMD, FLYAI_TIMEOUT

# 全局时间戳，确保两次flyai调用间隔≥15秒
_last_flyai_call = 0.0
_FLYAI_MIN_INTERVAL = 15.0


def _throttle():
    global _last_flyai_call
    elapsed = time.time() - _last_flyai_call
    if elapsed < _FLYAI_MIN_INTERVAL:
        wait = _FLYAI_MIN_INTERVAL - elapsed
        time.sleep(wait)
    _last_flyai_call = time.time()


class FlyaiClient:
    """飞猪命令行封装,只返回原始输出,不解析"""

    def _get_env(self) -> dict:
        env = os.environ.copy()
        return env

    def search_hotels_by_poi(self, dest_name: str, poi_name: str,
                             check_in: str, check_out: str,
                             max_price: int = None) -> str:
        """
        按景点名搜索附近酒店（主力方法）
        flyai search-hotels --dest-name 武汉 --poi-name 湖北省博物馆 --key-words 湖北省博物馆 --check-in-date 2026-04-16 --check-out-date 2026-04-17
        """
        _throttle()
        cmd = (f'{FLYAI_CMD} search-hotels '
               f'--dest-name "{dest_name}" '
               f'--poi-name "{poi_name}" '
               f'--key-words "{poi_name}" '
               f'--check-in-date {check_in} '
               f'--check-out-date {check_out} ')
        if max_price:
            cmd += f' --max-price {max_price}'
        try:
            print(cmd)
            r = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=60,
                env=self._get_env(),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("flyai search-hotels 超时")
        return r.stdout + r.stderr

    # ai-search 已注释，不再使用
    # def ai_search(self, query: str) -> str:
    #     ...

    def search_hotel(self, dest_name: str, check_in: str, check_out: str,
                     max_price: int = None) -> str:
        """结构化酒店搜索（备选）"""
        _throttle()
        cmd = (f'{FLYAI_CMD} search-hotel --dest-name "{dest_name}" '
               f'--check-in-date {check_in} --check-out-date {check_out} ')
        if max_price:
            cmd += f' --max-price {max_price}'
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=60,
                env=self._get_env(),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("flyai search-hotel 超时")
        return r.stdout + r.stderr
