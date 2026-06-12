#!/usr/bin/env python3
"""
adapters/qyyjt_adapter.py — v1.1.0 企业预警通数据适配器

华尔街驻铁岭办事处 · 企业预警通 (qyyjt.cn) 集成

三层次数据获取策略:
  Layer 1 (公开): WebSearch + WebFetch 抓取公开可见数据, 零依赖
  Layer 2 (账号): Selenium 模拟登录 → 提取 token → 调用内部 API
  Layer 3 (替代): 阿里云API市场 / 腾讯云 企业风险API 兜底

参考来源:
  - DanCheng2021/crawl-python (qyyjt.cn 爬虫)
  - YukidokeAzarea/QYYJTScraper (债券公告爬虫)
"""

from __future__ import annotations

import json
import hashlib
import time
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# 数据模块枚举 — 企业预警通 internal API dataId 映射
# ═══════════════════════════════════════════════════════════════

class QYJTModule(Enum):
    """企业预警通内部 dataId → 数据模块映射"""

    # 企业基础
    ENTERPRISE_BASIC = "101"        # 企业基本信息
    ENTERPRISE_PROFILE = "102"      # 企业画像/全景
    SHAREHOLDER_INFO = "103"        # 股东信息
    BRANCH_INFO = "104"             # 分支机构

    # 风险预警
    RISK_SCAN = "201"               # 企业风险扫描(综合)
    COURT_RECORDS = "202"           # 司法涉诉
    ADMIN_PENALTY = "203"           # 行政处罚
    CREDIT_RISK = "204"             # 信用风险(失信/限消)
    TAX_RISK = "205"                # 税务风险

    # 舆情
    NEWS_NEGATIVE = "301"           # 负面舆情
    NEWS_ALL = "302"                # 全部新闻
    PUBLIC_OPINION = "303"          # 舆情分析

    # 经营
    FINANCIAL_DATA = "401"          # 财务数据
    BOND_INFO = "402"               # 债券信息
    GUARANTEE_INFO = "403"          # 对外担保
    PLEDGE_INFO = "404"             # 股权质押

    # 关联
    RELATED_PARTIES = "501"         # 关联方
    UBO_CHAIN = "502"               # 受益所有人链
    GROUP_NETWORK = "503"           # 集团关系网络

    # 区域
    REGION_CODE = "154"             # 行政区划代码
    REGION_ECONOMY = "486"          # 区域经济与债务


@dataclass
class QYJTSession:
    """企业预警通登录会话"""
    token: str = ""                 # s_tk 短令牌 (~10min过期)
    refresh_token: str = ""         # r_tk 刷新令牌
    user_id: str = ""               # user ID
    cookies: Dict[str, str] = field(default_factory=dict)
    raw_cookie: str = ""            # Cookie 原始字符串
    login_time: float = 0.0
    token_expiry: float = 600       # 默认10分钟


# ═══════════════════════════════════════════════════════════════
# 主适配器
# ═══════════════════════════════════════════════════════════════

class QYJTAdapter:
    """
    企业预警通数据适配器

    使用方式:
        adapter = QYJTAdapter()

        # Layer 1: 公开数据 (无需登录)
        data = adapter.search_public("特斯拉")

        # Layer 2: 登录后API (需要账号)
        adapter.login_via_selenium("username", "password", manual_captcha=True)
        risk = adapter.call_api(QYJTModule.RISK_SCAN, company="特斯拉")

        # Layer 3: 第三方替代API
        risk_alt = adapter.call_alternative_api("特斯拉")

    分层获取策略:
        1. 先尝试 Layer 1 (免费公开) — 覆盖企业基础信息、新闻
        2. Layer 1 不够 → 尝试 Layer 2 (需要账号) — 覆盖风险、司法、财务
        3. Layer 2 不可用 → 尝试 Layer 3 (第三方API) — 兜底
        4. 全部失败 → 降级到 WebSearch
    """

    BASE_URL = "https://www.qyyjt.cn"
    API_ENDPOINT = f"{BASE_URL}/getData.action"
    LOGIN_URL = f"{BASE_URL}/user/login"
    SEARCH_URL = f"{BASE_URL}/search"

    def __init__(self, session_path: str = ".wallstreet/qyyjt_session.json"):
        self.session = QYJTSession()
        self.session_path = Path(session_path)
        self._lock = threading.RLock()

        # 结果缓存 (避免重复请求)
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl = 300  # 5分钟

        # 调用统计
        self._stats = {"layer1": 0, "layer2": 0, "layer3": 0, "fallback": 0}

        # 加载持久化会话
        self._load_session()

    # ── Layer 1: 公开数据 (WebSearch-based) ───────────────

    def search_public(self, company: str) -> Dict[str, Any]:
        """
        通过 WebSearch 抓取企业预警通公开可见数据。

        返回:
            {
                "source": "qyyjt_public",
                "company": company,
                "risk_signals": [...],       # 风险信号列表
                "news_items": [...],          # 相关新闻
                "basic_info": {...},          # 基本信息
                "urls": [...]                 # 原始链接
            }
        """
        self._stats["layer1"] += 1
        cache_key = f"public_{company}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        result = {
            "source": "qyyjt_public",
            "company": company,
            "risk_signals": [],
            "news_items": [],
            "basic_info": {},
            "urls": [],
            "fetched_at": datetime.now().isoformat(),
        }

        # 这里由上层 WebSearch engine 实际执行搜索
        # 返回的是结构化指令，告诉上层该搜什么
        result["_search_queries"] = [
            f"site:qyyjt.cn {company} 风险",
            f"site:qyyjt.cn {company} 司法",
            f"site:qyyjt.cn {company} 舆情",
            f"{company} 企业预警通 风险扫描",
        ]

        self._cache_set(cache_key, result)
        return result

    # ── Layer 2: 登录 + 内部 API ──────────────────────────

    def login_via_selenium(self, username: str, password: str,
                           manual_captcha: bool = True,
                           timeout: int = 60) -> bool:
        """
        Selenium 模拟登录，获取认证令牌。

        Args:
            username: 企业预警通用户名 (手机号)
            password: 密码
            manual_captcha: True=手动输入验证码, False=尝试OCR
            timeout: 登录超时 (秒)

        Returns:
            是否登录成功
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except ImportError:
            raise ImportError(
                "Selenium 未安装。安装: pip install selenium\n"
                "还需要 ChromeDriver: https://chromedriver.chromium.org/"
            )

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # 无头模式
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, timeout)

        try:
            # 1. 打开登录页
            driver.get(self.LOGIN_URL)
            time.sleep(2)

            # 2. 填写表单
            username_input = driver.find_element(By.ID, "username")
            username_input.send_keys(username)

            password_input = driver.find_element(By.ID, "password")
            password_input.send_keys(password)

            # 3. 验证码 — 等待用户手动输入
            if manual_captcha:
                print("\n[企业预警通] 请在浏览器中手动输入验证码，然后按 Enter 继续...")
                input()
            else:
                # 尝试简单 OCR (需要额外依赖)
                self._solve_captcha(driver)

            # 4. 点击登录
            login_btn = driver.find_element(
                By.CSS_SELECTOR, "#rc-tabs-0-panel-0 > form button[type='submit']"
            )
            login_btn.click()
            time.sleep(10)  # 等待登录完成

            # 5. 提取凭据
            cookies = driver.get_cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

            # localStorage 中的令牌
            s_tk = driver.execute_script("return localStorage.getItem('s_tk');") or ""
            r_tk = driver.execute_script("return localStorage.getItem('r_tk');") or ""
            u_info_raw = driver.execute_script("return localStorage.getItem('u_info');") or "{}"

            u_info = json.loads(u_info_raw)
            user_id = u_info.get("user", "")

            if not s_tk or not user_id:
                print("[企业预警通] 登录失败: 未获取到认证令牌")
                return False

            # 去除 s_tk 外层引号
            token = s_tk.strip('"\'') if s_tk else ""

            self.session = QYJTSession(
                token=token,
                refresh_token=r_tk.strip('"\''),
                user_id=user_id,
                raw_cookie=cookie_str,
                login_time=time.time(),
            )

            self._save_session()
            print(f"[企业预警通] 登录成功: user={user_id}")
            return True

        except Exception as e:
            print(f"[企业预警通] 登录异常: {e}")
            return False
        finally:
            driver.quit()

    def call_api(self, module: QYJTModule, **params) -> Dict[str, Any]:
        """
        调用企业预警通内部 API。

        Args:
            module: 数据模块 (如 QYJTModule.RISK_SCAN)
            **params: 查询参数 (company, keyword, regionCode, datetime 等)

        Returns:
            API 响应 JSON
        """
        # 检查 token 是否过期
        if not self._token_valid():
            if self.session.refresh_token:
                self._refresh_token()
            else:
                raise RuntimeError(
                    "企业预警通 token 已过期，需要重新登录。\n"
                    "调用 login_via_selenium(username, password)"
                )

        headers = self._build_headers(module)
        url = self._build_url(module, params)

        try:
            import requests
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self._stats["layer2"] += 1
            return data
        except Exception as e:
            print(f"[企业预警通] API 调用失败 ({module.value}): {e}")
            return {"error": str(e), "module": module.value}

    def search_company_risk(self, company: str) -> Dict[str, Any]:
        """快捷方法: 企业风险综合查询"""
        result = {"company": company, "source": "qyyjt_internal"}

        # 风险扫描
        risk = self.call_api(QYJTModule.RISK_SCAN, keyword=company)
        result["risk"] = self._parse_risk_response(risk)

        # 司法涉诉
        court = self.call_api(QYJTModule.COURT_RECORDS, keyword=company)
        result["court"] = self._parse_court_response(court)

        # 负面舆情
        news = self.call_api(QYJTModule.NEWS_NEGATIVE, keyword=company)
        result["news"] = self._parse_news_response(news)

        return result

    # ── Layer 3: 第三方替代API ───────────────────────────

    def call_alternative_api(self, company: str) -> Dict[str, Any]:
        """
        通过阿里云API市场 / 腾讯云 获取企业风险数据。

        替代方案:
          - 阿里云: 企业信号详情API
          - 腾讯云: 企业风险报告API
          - 天眼查MCP (已有集成)
          - 企查查MCP (已有集成)
        """
        self._stats["layer3"] += 1
        result = {"company": company, "source": "alternative_api", "methods": []}

        # 阿里云API市场 — 企业信号详情
        # 接口: https://market.aliyun.com/apimarket/detail/cmapi00068436
        # 需要 AppCode
        result["methods"].append({
            "name": "aliyun_enterprise_signal",
            "description": "企业信号详情API — 风险信号等级/标签/摘要",
            "url": "https://jqyzqyxx.market.alicloudapi.com/enterprise/signal",
            "requires": "AppCode (阿里云API网关)",
        })

        # 腾讯云 — 企业风险报告
        result["methods"].append({
            "name": "tencent_enterprise_risk",
            "description": "企业风险报告API — 司法/税务/合同履约",
            "url": "https://cloud.tencent.com/product/erp",
            "requires": "SecretId + SecretKey (腾讯云)",
        })

        return result

    # ── 公共接口: 统一查询 ──────────────────────────────

    def query(self, company: str, modules: Optional[List[QYJTModule]] = None) -> Dict[str, Any]:
        """
        智能查询 — 自动选择最佳数据获取路径。

        优先级: Layer 1 (公开) → Layer 2 (内部API) → Layer 3 (第三方) → Fallback

        Args:
            company: 公司名称
            modules: 需要的模块列表 (None=全部)

        Returns:
            综合查询结果
        """
        result = {
            "company": company,
            "timestamp": datetime.now().isoformat(),
            "layers_used": [],
            "data": {},
        }

        # Layer 1 永远是第一步 — 零成本
        public = self.search_public(company)
        result["data"]["public"] = public
        result["layers_used"].append("layer1")

        # Layer 2 — 如果有有效 session
        if self._token_valid():
            try:
                internal = self.search_company_risk(company)
                result["data"]["internal"] = internal
                result["layers_used"].append("layer2")
            except Exception as e:
                result["data"]["internal_error"] = str(e)

        # Layer 3 — 如果前两层数据不足
        if "internal" not in result["data"] or not result["data"].get("internal", {}).get("risk"):
            result["data"]["alternative"] = self.call_alternative_api(company)
            result["layers_used"].append("layer3")

        return result

    # ── 内部辅助方法 ────────────────────────────────────

    def _token_valid(self) -> bool:
        """检查 token 是否还有效"""
        if not self.session.token:
            return False
        elapsed = time.time() - self.session.login_time
        return elapsed < self.session.token_expiry

    def _refresh_token(self) -> bool:
        """尝试用 refresh_token 续期"""
        # 企业预警通的 refresh 机制未知
        # 这里先返回 False，触发重新登录
        print("[企业预警通] token 过期，需要重新登录")
        return False

    def _build_headers(self, module: QYJTModule) -> Dict[str, str]:
        """构建 API 请求头"""
        return {
            "PCUSS": self.session.token,
            "user": self.session.user_id,
            "cookie": self.session.raw_cookie,
            "dataId": module.value,
            "system": "new",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.qyyjt.cn/",
        }

    def _build_url(self, module: QYJTModule, params: Dict) -> str:
        """构建 API URL"""
        base = self.API_ENDPOINT
        query_parts = []

        if module == QYJTModule.REGION_ECONOMY:
            query_parts = [
                f"keyword={params.get('keyword', '')}",
                "func=/app/regionalEconomic2",
                "module_type=area_economy_and_debt",
                "dateQueryType=1",
                f"size={params.get('size', 100)}",
                f"indicName={params.get('indicName', '')}",
                f"datetime={params.get('datetime', '2024')}",
                f"regionCode={params.get('regionCode', '')}",
            ]
        else:
            # 通用查询
            keyword = params.get("keyword", params.get("company", ""))
            query_parts = [f"keyword={keyword}"]

        query_string = "&".join(q for q in query_parts if q)
        return f"{base}?{query_string}" if query_string else base

    def _parse_risk_response(self, raw: Dict) -> Dict:
        """解析风险扫描响应"""
        if not raw or "data" not in raw:
            return {"signals": [], "summary": "无数据"}
        data = raw.get("data", {})
        return {
            "signals": data.get("return1", []) or data.get("signals", []),
            "summary": data.get("summary", ""),
            "risk_level": data.get("riskLevel", data.get("level", "unknown")),
        }

    def _parse_court_response(self, raw: Dict) -> Dict:
        """解析司法涉诉响应"""
        return {"cases": raw.get("data", {}).get("return1", []) if raw else []}

    def _parse_news_response(self, raw: Dict) -> Dict:
        """解析舆情新闻响应"""
        return {"items": raw.get("data", {}).get("return1", []) if raw else []}

    def _solve_captcha(self, driver) -> bool:
        """尝试自动识别验证码 (需要额外依赖)"""
        # 简单实现: 截图 + 基础 OCR
        # 生产环境建议接入打码平台
        try:
            from PIL import Image
            import io
            # 找到验证码元素并截图
            captcha_img = driver.find_element(By.CSS_SELECTOR, "img.captcha")
            screenshot = captcha_img.screenshot_as_png

            # 这里需要接入 OCR (pytesseract / ddddocr)
            # 暂略 — 默认使用 manual_captcha=True
            return False
        except Exception:
            return False

    # ── 缓存 ────────────────────────────────────────────

    def _cache_get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                ts, val = self._cache[key]
                if time.time() - ts < self._cache_ttl:
                    return val
                del self._cache[key]
        return None

    def _cache_set(self, key: str, value: Any):
        with self._lock:
            self._cache[key] = (time.time(), value)

    # ── 持久化 ──────────────────────────────────────────

    def _save_session(self):
        """保存登录会话到磁盘"""
        data = {
            "token": self.session.token,
            "refresh_token": self.session.refresh_token,
            "user_id": self.session.user_id,
            "raw_cookie": self.session.raw_cookie,
            "login_time": self.session.login_time,
        }
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(json.dumps(data))

    def _load_session(self):
        """从磁盘加载登录会话"""
        if self.session_path.is_file():
            try:
                data = json.loads(self.session_path.read_text())
                self.session = QYJTSession(**data)
            except Exception:
                pass

    def get_stats(self) -> dict:
        return dict(self._stats)


# ═══════════════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="企业预警通数据查询")
    parser.add_argument("company", help="公司名称")
    parser.add_argument("--login", action="store_true", help="先登录")
    parser.add_argument("--username", help="用户名(手机号)")
    parser.add_argument("--password", help="密码")
    args = parser.parse_args()

    adapter = QYJTAdapter()

    if args.login and args.username:
        adapter.login_via_selenium(args.username, args.password)

    result = adapter.query(args.company)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
