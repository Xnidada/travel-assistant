"""小红书 MCP 客户端封装"""
import json
import os
import subprocess
import sys
from config import XHS_SCRIPT, XHS_TIMEOUT


class XhsClient:
    """小红书MCP命令行封装，只返回原始输出，不解析"""

    def check_login(self) -> bool:
        out = self._run("check_login_status", {})
        print(f'DEBUG: check_login 输出: {out[:200]}...' if len(out) > 200 else f'DEBUG: check_login 输出: {out}')
        try:
            # 尝试解析 JSON 输出
            import json
            data = json.loads(out)
            # 检查是否有登录成功的信息
            text = data.get('result', {}).get('content', [{}])[0].get('text', '')
            print(f'DEBUG: 解析后的文本: {text}')
            return "已登录" in text
        except Exception as e:
            print(f'DEBUG: JSON解析失败: {e}')
            # 如果解析失败，回退到字符串查找
            return "已登录" in out

    def search_feeds(self, keyword: str) -> str:
        return self._run("search_feeds", {"keyword": keyword})

    def get_feed_detail(self, feed_id: str, xsec_token: str) -> str:
        return self._run("get_feed_detail", {
            "feed_id": feed_id,
            "xsec_token": xsec_token,
            "load_all_comments": False,
            "limit": 10,
        })

    def _run(self, method: str, params: dict) -> str:
        args_json = json.dumps(params, ensure_ascii=False)
        cmd = f"{XHS_SCRIPT} {method} '{args_json}'"
        print(f"DEBUG _run: 执行命令: {cmd}")
        try:
            # 设置环境变量，避免代理问题
            env = os.environ.copy()
            env['http_proxy'] = ''
            env['https_proxy'] = ''
            env['HTTP_PROXY'] = ''
            env['HTTPS_PROXY'] = ''
            
            r = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=XHS_TIMEOUT, env=env
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"小红书命令超时: {method}")

        if r.returncode != 0:
            raise RuntimeError(f"小红书命令失败({method}): {r.stderr[:300]}")
        #print(f'DEBUG _run: {r.stdout}')
        print(f'DEBUG _run: stdout长度={len(r.stdout)}, stderr长度={len(r.stderr)}')
        if r.stderr:
            print(f'DEBUG _run stderr: {r.stderr[:200]}')
        return r.stdout


if __name__ == "__main__":
    c = XhsClient()
    print("登录状态:", c.check_login())
