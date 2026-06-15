# """AI 分析器 — 通过 openclaw infer model run 调用模型分析非结构化文本"""
# import json
# import re
# import subprocess
# import sys
# import os

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from config import MODEL_NAME


# # 模型名映射
# _MODEL_MAP = {
#     "glm5.1": "glm5-1/glm-5.1",
#     "glm-5.1": "glm5-1/glm-5.1",
#     "deepseek": "deepseek-v3.2/deepseek-v3.2",
#     "hw/deepseek-v3.2": "hw/deepseek-v3.2",
#     "deepseek-v3.2": "hw/deepseek-v3.2",
# }


# class AIAnalyzer:
#     """所有非结构化文本的解析都通过模型完成，不使用正则提取业务数据"""

#     def __init__(self):
#         model_id = _MODEL_MAP.get(MODEL_NAME, MODEL_NAME)
#         # 如果不包含 /，尝试补全
#         if "/" not in model_id:
#             model_id = f"{model_id}/{model_id}"
#         self.model_id = model_id

#     def analyze(self, raw_text: str, prompt: str) -> dict | list:
#         """
#         将原始文本和提示词交给模型分析，返回结构化JSON结果。
#         """
#         full_prompt = f"""{prompt}

# ---原始数据开始---
# {raw_text}
# ---原始数据结束---

# 请严格按照要求的JSON格式返回，不要添加额外解释文字，只返回JSON。"""

#         result_text = self._call_model(full_prompt)
#         return self._extract_json(result_text)

#     def _call_model(self, prompt: str, retries: int = 2) -> str:
#         """通过 openclaw infer model run 调用模型"""
#         for attempt in range(retries + 1):
#             try:
#                 r = subprocess.run(
#                     ["openclaw", "infer", "model", "run",
#                      "--model", self.model_id,
#                      "--prompt", prompt],
#                     capture_output=True, text=True, timeout=120,
#                 )
#                 if r.returncode == 0 and r.stdout.strip():
#                     # 输出可能包含 "model: xxx\noutputs: 1\n" 前缀
#                     output = r.stdout.strip()
#                     # 去掉开头的元数据行
#                     lines = output.split("\n")
#                     content_lines = []
#                     skip = True
#                     for line in lines:
#                         if skip and (line.startswith("model:") or line.startswith("outputs:")):
#                             continue
#                         skip = False
#                         content_lines.append(line)
#                     return "\n".join(content_lines).strip()
#             except subprocess.TimeoutExpired:
#                 print(f"   ⚠️  模型调用超时 (attempt {attempt+1})")
#             except Exception as e:
#                 print(f"   ⚠️  模型调用异常 (attempt {attempt+1}): {e}")

#         raise RuntimeError(f"模型调用失败（重试{retries}次后），请检查 openclaw 配置")

#     def _extract_json(self, text: str) -> dict | list:
#         """从模型输出中提取JSON"""
#         text = text.strip()
#         # 尝试直接解析
#         try:
#             return json.loads(text)
#         except json.JSONDecodeError:
#             pass

#         # 提取 ```json ... ``` 块
#         m = re.search(r'```json\s*([\s\S]*?)\s*```', text)
#         if m:
#             try:
#                 return json.loads(m.group(1))
#             except json.JSONDecodeError:
#                 pass

#         # 提取 ``` ... ``` 块
#         m = re.search(r'```\s*([\s\S]*?)\s*```', text)
#         if m:
#             try:
#                 return json.loads(m.group(1))
#             except json.JSONDecodeError:
#                 pass

#         # 提取最外层 { } 或 [ ]
#         for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
#             m = re.search(pattern, text)
#             if m:
#                 try:
#                     return json.loads(m.group(0))
#                 except json.JSONDecodeError:
#                     pass

#         raise ValueError(f"无法从模型输出中提取JSON，输出前300字: {text[:300]}")


# # 单例
# analyzer = AIAnalyzer()

"""AI 分析器 — 通过 ModelArts MaaS API 调用模型分析非结构化文本"""
import json
import re
import os
import sys
import requests

# 添加项目根目录到 sys.path（确保能导入 config）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_NAME, MAAS_API_KEY, MAAS_API_URL

REQUEST_TIMEOUT = 120
MODEL_ID = "qwen3-30b-a3b"  # 固定使用该模型

# 模型上下文限制（保守值）
MAX_CONTEXT_TOKENS = 131072
# 预留输出空间（根据任务调整）
MAX_COMPLETION_TOKENS = 4096
# 估算：1 token ≈ 0.75 中文字符 → 可输入字符数上限
MAX_INPUT_CHARS = int((MAX_CONTEXT_TOKENS - MAX_COMPLETION_TOKENS) * 0.75)


class AIAnalyzer:
    """所有非结构化文本的解析都通过远程大模型完成"""

    def __init__(self):
        if not MAAS_API_KEY or MAAS_API_KEY == "your_actual_api_key_here":
            raise ValueError("请在 config.py 中正确配置 MAAS_API_KEY")
        self.model_id = MODEL_ID
        self.api_url = MAAS_API_URL
        self.api_key = MAAS_API_KEY

    def analyze(self, raw_text: str, prompt: str) -> dict | list:
        """
        将原始文本和提示词交给模型分析，返回结构化JSON结果。
        自动分块处理超长文本，并聚合结果。
        """
        if len(raw_text) <= MAX_INPUT_CHARS:
            # 直接分析
            return self._analyze_chunk(raw_text, prompt)
        else:
            # 分块处理
            chunks = self._split_text(raw_text, MAX_INPUT_CHARS)
            results = []
            for i, chunk in enumerate(chunks):
                print(f"   📦 分析第 {i+1}/{len(chunks)} 块...")
                result = self._analyze_chunk(chunk, prompt)
                results.append(result)
            # 最终聚合
            return self._aggregate_results(results, prompt)

    def _split_text(self, text: str, max_chars: int) -> list[str]:
        """简单按字符长度分块（可优化为按语义分段）"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            # 尽量在换行处分割
            if end < len(text):
                newline_pos = text.rfind('\n', start, end)
                if newline_pos != -1:
                    end = newline_pos
            chunks.append(text[start:end])
            start = end
        return chunks

    def _analyze_chunk(self, chunk: str, prompt: str) -> dict | list:
        user_content = f"""{prompt}

---原始数据开始---
{chunk}
---原始数据结束---

请严格按照要求的JSON格式返回，不要添加额外解释文字，只返回JSON。"""

        messages = [
            {"role": "system", "content": "You are a precise data extraction assistant. Always output valid JSON."},
            {"role": "user", "content": user_content}
        ]

        result_text = self._call_model(messages)
        return self._extract_json(result_text)

    def _aggregate_results(self, results: list, original_prompt: str) -> dict | list:
        """将多个分析结果合并成最终结果"""
        aggregation_prompt = f"""你是一个旅游信息整合专家。以下是多段哈尔滨旅游笔记的分析结果（JSON格式列表）。
请将它们合并成一个统一的JSON结果，去重并保留最完整的信息。

要求：
- 输出格式必须与原始分析格式一致（如包含景点、美食、避雷等字段）
- 合并相同名称的条目
- 不要丢失任何有效信息

---多段分析结果开始---
{json.dumps(results, ensure_ascii=False, indent=2)}
---多段分析结果结束---

请只返回合并后的JSON，不要任何其他文字。"""

        messages = [
            {"role": "system", "content": "You are a data fusion expert. Output only valid JSON."},
            {"role": "user", "content": aggregation_prompt}
        ]

        result_text = self._call_model(messages, max_completion_tokens=8192)
        return self._extract_json(result_text)

    def _call_model(self, messages: list, max_completion_tokens: int = None, retries: int = 2) -> str:
        """通过 ModelArts MaaS API 调用模型"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        # 使用传入的 max_completion_tokens，否则用默认值
        max_tokens = max_completion_tokens if max_completion_tokens is not None else MAX_COMPLETION_TOKENS
        data = {
            "model": self.model_id,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": max_tokens  # ⚠️ 不再是 128000！
        }

        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    data=json.dumps(data),
                    timeout=REQUEST_TIMEOUT
                )
                if response.status_code == 200:
                    resp_json = response.json()
                    content = resp_json["choices"][0]["message"]["content"].strip()
                    return content
                else:
                    print(f"   ⚠️  API 返回错误 (attempt {attempt+1}): {response.status_code} - {response.text}")
            except requests.Timeout:
                print(f"   ⚠️  API 请求超时 (attempt {attempt+1})")
            except Exception as e:
                print(f"   ⚠️  API 调用异常 (attempt {attempt+1}): {e}")

        raise RuntimeError(f"模型 API 调用失败（重试{retries}次后），请检查 config.py 中的 MAAS_API_KEY 或网络")

    def _extract_json(self, text: str) -> dict | list:
        """从模型输出中提取JSON（保持原有逻辑）"""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试 ```json ... ```
        m = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试 ``` ... ```
        m = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试最外层 {} 或 []
        for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
            m = re.search(pattern, text)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass

        raise ValueError(f"无法从模型输出中提取JSON，输出前300字: {text[:300]}")


# 单例
analyzer = AIAnalyzer()