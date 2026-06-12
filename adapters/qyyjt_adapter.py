#!/usr/bin/env python3
"""
adapters/qyyjt_adapter.py — v1.1.0 企业预警通全功能适配器

华尔街驻铁岭办事处 · qyyjt.cn 全面集成

数据获取四层策略:
  Layer 0: 公开页面 WebSearch → 不登录也能拿的基础信息
  Layer 1: 新版 REST API (finchinaAPP/v1/) → 多重搜索 + 债券/公告
  Layer 2: 旧版内部 API (getData.action) → 区域经济 + dataId模块
  Layer 3: 第三方替代API → 阿里云/腾讯云兜底

参考来源:
  - DanCheng2021/crawl-python: 旧版API (dataId=154/486)
  - YukidokeAzarea/QYYJTScraper: 新版REST API (multipleSearch/F9公告)
  - caifuhao.eastmoney.com: 产品功能全图
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("qyyjt")


# ═══════════════════════════════════════════════════════════════
# 数据模块 — 企业预警通全部功能映射
# ═══════════════════════════════════════════════════════════════

class QYJTModule(Enum):
    """企业预警通功能模块 — 按产品功能全图组织"""

    # ── 新版 REST API (finchinaAPP/v1/) ──
    SEARCH_MULTI = "search_multi"        # 企业/证券/综合搜索
    BOND_NOTICE = "bond_notice"          # 债券公告列表 (F9深度资料)

    # ── 企业尽调 ──
    ENTERPRISE_BASIC = "ent_basic"       # 工商信息
    ENTERPRISE_CREDIT = "ent_credit"     # 信用报告
    ENTERPRISE_PENALTY = "ent_penalty"   # 行政处罚
    ENTERPRISE_FINANCING = "ent_finance" # 融资信息
    ENTERPRISE_CHANGE = "ent_change"     # 工商变更

    # ── 风险扫描 ──
    RISK_SCAN = "risk_scan"             # 企业风险扫描(综合)
    RISK_SIGNAL = "risk_signal"         # 风险信号详情(等级/标签/摘要)
    COURT_CASES = "court_cases"         # 裁判文书
    COURT_ANNOUNCE = "court_announce"   # 开庭公告
    DISHONESTY = "dishonesty"           # 失信被执行人
    LIMIT_HIGH = "limit_high"           # 限制高消费
    EXECUTION = "execution"             # 执行信息

    # ── 舆情监控 ──
    NEWS_NEGATIVE = "news_negative"     # 负面舆情
    NEWS_ALL = "news_all"               # 全部新闻
    RESEARCH_REPORT = "research"        # 研报

    # ── 财务数据 ──
    FINANCIAL_STATEMENT = "financial"   # 财务报表
    FINANCIAL_INDICATORS = "fin_indic"  # 财务指标

    # ── 债券专项 ──
    BOND_PROFILE = "bond_profile"       # 债券深度资料
    BOND_CREDIT = "bond_credit"         # 债券信用评级
    CITY_INVEST = "city_invest"         # 城投专题 (200+指标)

    # ── 区域经济 ──
    REGION_CODE = "region_code"         # 地区代码 (dataId=154)
    REGION_ECONOMY = "region_economy"   # 区域经济 (dataId=486)
    REGION_DEBT = "region_debt"         # 地方债务

    # ── 关联方 ──
    RELATED_PARTIES = "related"         # 关联方
    UBO_CHAIN = "ubo"                   # 受益所有人
    GROUP_NETWORK = "group"             # 集团网络

    # ── 金融机构 ──
    FIN_INSTITUTION = "fin_inst"        # 金融机构百科 (15大类)

    # ── 监控 ──
    WATCHLIST = "watchlist"             # 自选组合监控
    ALERT_PUSH = "alert_push"           # 预警推送


# ═══════════════════════════════════════════════════════════════
# 端点注册表 — 所有已知的 API 端点
# ═══════════════════════════════════════════════════════════════

@dataclass
class Endpoint:
    """单个 API 端点定义"""
    key: str                           # 端点标识
    url: str                           # 完整URL或路径
    method: str = "GET"                # GET/POST
    api_type: str = "rest"             # rest / legacy / public
    description: str = ""
    params_template: Dict = field(default_factory=dict)  # 默认参数
    headers_template: Dict = field(default_factory=dict)  # 额外请求头
    dataId: Optional[str] = None       # 旧版API的dataId


ENDPOINTS: Dict[str, Endpoint] = {
    # ── 新版 REST API ──
    "search_multi": Endpoint(
        key="search_multi",
        url="/finchinaAPP/v1/finchina-search/v1/multipleSearch",
        method="GET",
        api_type="rest",
        description="多重搜索: 企业/证券/综合",
        params_template={"pagesize": 10, "skip": 0, "template": "list", "isRelationSearch": 0},
    ),
    "bond_notice": Endpoint(
        key="bond_notice",
        url="/finchinaAPP/v1/finchina-search/v1/webNotice/getF9NoticeList",
        method="POST",
        api_type="rest",
        description="债券公告列表 (F9深度资料)",
        params_template={"type": "co", "skip": 0, "size": 10, "oneLevelItemCode": "50", "f9Below": "true"},
        headers_template={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
    ),

    # ── 旧版内部 API (getData.action) ──
    "region_code": Endpoint(
        key="region_code",
        url="/getData.action",
        method="GET",
        api_type="legacy",
        description="行政区划代码查询",
        dataId="154",
    ),
    "region_economy": Endpoint(
        key="region_economy",
        url="/getData.action",
        method="GET",
        api_type="legacy",
        description="区域经济与债务指标 (3000+行政区)",
        dataId="486",
        params_template={
            "func": "/app/regionalEconomic2",
            "module_type": "area_economy_and_debt",
            "dateQueryType": "1",
            "size": "10000",
        },
    ),
}


# ═══════════════════════════════════════════════════════════════
# 会话管理
# ═══════════════════════════════════════════════════════════════

@dataclass
class QYJTSession:
    """企业预警通登录会话"""
    token_name: str = "PCUSS"          # 新版用 token_name, 旧版固定 PCUSS
    token_value: str = ""              # s_tk 短令牌
    refresh_token: str = ""            # r_tk
    user_id: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    raw_cookie: str = ""
    login_time: float = 0.0
    token_ttl: float = 540             # 9分钟安全期 (<10分钟过期)


# ═══════════════════════════════════════════════════════════════
# 主适配器
# ═══════════════════════════════════════════════════════════════

class QYJTAdapter:
    """
    企业预警通全功能适配器

    用法:
        a = QYJTAdapter()
        a.login_via_selenium("138xxxx", "password")

        # 搜索
        r = a.search("特斯拉")                         # REST API
        r = a.search_company("特斯拉")                 # 综合查询

        # 债券
        r = a.get_bond_notices("bond_code_123")        # 债券公告

        # 区域经济
        codes = a.get_region_codes()                   # 省市县代码
        r = a.get_region_economy("2024", "310000")     # 区域经济指标

        # 智能查询（自动选最优路径）
        r = a.query("特斯拉", modules=[QYJTModule.RISK_SCAN, QYJTModule.COURT_CASES])
    """

    BASE_URL = "https://www.qyyjt.cn"
    LOGIN_URL = f"{BASE_URL}/user/login"

    def __init__(self, session_path: str = ".wallstreet/qyyjt_session.json"):
        self.session = QYJTSession()
        self.session_path = Path(session_path)
        self._lock = threading.RLock()
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl = 300

        # 请求计数 (用于速率限制)
        self._request_count = 0
        self._rate_limit_window = 60  # 每分钟最多请求数
        self._rate_limit_max = 30     # 保守值

        # 统计
        self._stats = {"rest": 0, "legacy": 0, "public": 0, "errors": 0}

        self._load_session()
        self._time_provider = time.time

    # ═══════════════════════════════════════════════════════
    # 登录
    # ═══════════════════════════════════════════════════════

    def login_via_selenium(self, username: str, password: str,
                           headless: bool = True) -> bool:
        """
        Selenium 模拟登录。

        流程: 打开登录页 → 填写手机号密码 → 等待手动输入验证码 →
              点击登录 → 从 localStorage 提取 s_tk/r_tk/u_info
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except ImportError:
            raise ImportError("pip install selenium + ChromeDriver")

        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,800")

        driver = webdriver.Chrome(options=options)

        try:
            driver.get(self.LOGIN_URL)
            time.sleep(2)

            # 切换到密码登录tab
            try:
                pwd_tab = driver.find_element(By.XPATH, "//div[text()='账户密码登录']")
                pwd_tab.click()
                time.sleep(0.5)
            except Exception:
                pass

            # 填写
            phone = driver.find_element(By.XPATH, "//input[@placeholder='请输入手机号']")
            phone.send_keys(username)

            pwd_input = driver.find_element(By.XPATH, "//input[@type='password']")
            pwd_input.send_keys(password)

            print("\n[企业预警通] 请在浏览器中手动完成验证码, 然后按 Enter...")
            input()

            # 登录
            login_btn = driver.find_element(By.XPATH, "//button[contains(., '登 录')]")
            login_btn.click()
            time.sleep(8)

            # 提取凭据
            s_tk = driver.execute_script("return localStorage.getItem('s_tk');") or ""
            r_tk = driver.execute_script("return localStorage.getItem('r_tk');") or ""
            u_info_raw = driver.execute_script("return localStorage.getItem('u_info');") or "{}"
            u_info = json.loads(u_info_raw)

            cookies = driver.get_cookies()
            cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

            if not s_tk:
                print("[企业预警通] 登录失败: 未获取到 s_tk")
                return False

            self.session = QYJTSession(
                token_name="PCUSS",
                token_value=s_tk.strip('"\''),
                refresh_token=r_tk.strip('"\''),
                user_id=u_info.get("user", ""),
                raw_cookie=cookie_str,
                login_time=self._time_provider(),
            )

            self._save_session()
            print(f"[企业预警通] 登录成功 user={self.session.user_id}")
            return True

        except Exception as e:
            print(f"[企业预警通] 登录异常: {e}")
            return False
        finally:
            driver.quit()

    # ═══════════════════════════════════════════════════════
    # 新版 REST API 调用
    # ═══════════════════════════════════════════════════════

    def search(self, keyword: str, search_type: str = "all",
               page_size: int = 10) -> Dict[str, Any]:
        """
        多重搜索 — 新版 REST API

        Args:
            keyword: 搜索关键词 (企业名/证券名/功能)
            search_type: all / enterprise / security
            page_size: 每页结果数
        """
        ep = ENDPOINTS["search_multi"]
        self._rate_limit_check()

        params = dict(ep.params_template)
        params["text"] = keyword
        params["pagesize"] = page_size

        headers = self._build_rest_headers()
        headers["referer"] = f"{self.BASE_URL}/search?text={keyword}"

        try:
            resp = self._http_get(f"{self.BASE_URL}{ep.url}", headers=headers, params=params)
            data = resp.json()
            self._check_response_errors(data)
            self._stats["rest"] += 1
            return self._parse_search_result(data)
        except Exception as e:
            self._stats["errors"] += 1
            return {"error": str(e), "source": "qyyjt_rest", "endpoint": "search_multi"}

    def get_bond_notices(self, bond_code: str, page_size: int = 10,
                         skip: int = 0) -> Dict[str, Any]:
        """债券公告列表 (F9深度资料)"""
        ep = ENDPOINTS["bond_notice"]
        self._rate_limit_check()

        payload = dict(ep.params_template)
        payload["code"] = bond_code
        payload["skip"] = skip
        payload["size"] = page_size

        headers = self._build_rest_headers()
        headers["content-type"] = "application/x-www-form-urlencoded;charset=UTF-8"
        headers["origin"] = self.BASE_URL
        headers["referer"] = f"{self.BASE_URL}/bond/f9?code={bond_code}"

        try:
            resp = self._http_post(f"{self.BASE_URL}{ep.url}", headers=headers, data=payload)
            data = resp.json()
            self._check_response_errors(data)
            self._stats["rest"] += 1
            return self._parse_bond_notices(data)
        except Exception as e:
            self._stats["errors"] += 1
            return {"error": str(e), "source": "qyyjt_rest", "endpoint": "bond_notice"}

    # ═══════════════════════════════════════════════════════
    # 旧版内部 API
    # ═══════════════════════════════════════════════════════

    def get_region_codes(self) -> Dict[str, Any]:
        """获取全国省/市/县行政区划代码 (dataId=154)"""
        return self._call_legacy("region_code")

    def get_region_economy(self, year: str = "2024",
                           region_codes: str = "",
                           indicators: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        区域经济与债务指标 (dataId=486)

        Args:
            year: 年份
            region_codes: 逗号分隔的地区代码
            indicators: 指标列表, 默认16项核心指标
        """
        if indicators is None:
            indicators = [
                "地区生产总值", "人均地区生产总值", "GDP增速",
                "工业总产值", "固定资产投资", "进出口总额",
                "社会消费品零售总额", "社会消费品零售总额增速",
                "城镇居民人均可支配收入",
                "一般公共预算收入", "一般公共预算支出",
                "地方政府债务余额", "地方政府债务限额",
                "负债率", "债务率1",
            ]

        ep = ENDPOINTS["region_economy"]
        params = dict(ep.params_template)
        params["indicName"] = ",".join(indicators)
        params["datetime"] = year
        params["regionCode"] = region_codes

        return self._call_legacy("region_economy", extra_params=params)

    def _call_legacy(self, endpoint_key: str,
                     extra_params: Optional[Dict] = None) -> Dict[str, Any]:
        """调用旧版 API"""
        ep = ENDPOINTS.get(endpoint_key)
        if not ep:
            return {"error": f"Unknown endpoint: {endpoint_key}"}

        if not self._token_valid():
            return {"error": "token_expired", "hint": "需要重新登录"}

        self._rate_limit_check()

        headers = self._build_legacy_headers(ep)
        url = self.BASE_URL + ep.url

        try:
            resp = self._http_get(url, headers=headers, params=extra_params or {})
            data = resp.json()
            self._check_response_errors(data)
            self._stats["legacy"] += 1
            return data
        except Exception as e:
            self._stats["errors"] += 1
            return {"error": str(e), "source": "qyyjt_legacy", "endpoint": endpoint_key}

    # ═══════════════════════════════════════════════════════
    # 智能综合查询
    # ═══════════════════════════════════════════════════════

    def search_company(self, company: str) -> Dict[str, Any]:
        """
        企业综合查询 — 尽可能多地拉取数据。

        优先级: REST多重搜索 → 有token则继续爬详情
        """
        result = {
            "company": company,
            "timestamp": datetime.now().isoformat(),
            "layers": [],
            "data": {},
        }

        # Layer 1: REST 搜索
        search = self.search(company)
        result["data"]["search"] = search
        result["layers"].append("rest_search")

        # Layer 2: 如果有 token, 尝试更多
        if self._token_valid():
            try:
                # 尝试搜索债券相关信息
                if "list" in search:
                    for item in search.get("list", [])[:3]:
                        code = item.get("code", "")
                        if code:
                            result["data"][f"bond_{code}"] = self.get_bond_notices(code)
                result["layers"].append("rest_detail")
            except Exception as e:
                result["data"]["detail_error"] = str(e)

        return result

    def query(self, company: str,
              modules: Optional[List[QYJTModule]] = None) -> Dict[str, Any]:
        """
        全功能查询入口 — 按需调用所有可用数据源。

        没有账号时只走搜索+公开数据。
        """
        result = self.search_company(company)

        if not modules:
            modules = [QYJTModule.SEARCH_MULTI]

        for mod in modules:
            try:
                if mod == QYJTModule.SEARCH_MULTI:
                    continue  # 已经查过了
                elif mod == QYJTModule.BOND_NOTICE:
                    if "list" in result.get("data", {}).get("search", {}):
                        for item in result["data"]["search"].get("list", [])[:2]:
                            code = item.get("code", "")
                            if code:
                                result["data"]["bond_notices"] = self.get_bond_notices(code)
                elif mod == QYJTModule.REGION_ECONOMY:
                    if self._token_valid():
                        result["data"]["region"] = self.get_region_economy()
            except Exception as e:
                result["data"][f"{mod.value}_error"] = str(e)

        return result

    # ═══════════════════════════════════════════════════════
    # 公开数据 (无需登录)
    # ═══════════════════════════════════════════════════════

    def search_public(self, company: str) -> Dict[str, Any]:
        """
        Layer 0: 公开数据 — 不登录也能拿到的信息。

        返回结构化指令，由上层 WebSearch engine 实际执行。
        """
        self._stats["public"] += 1

        return {
            "source": "qyyjt_public",
            "company": company,
            "fetched_at": datetime.now().isoformat(),
            "_queries": [
                f"site:qyyjt.cn {company} 风险",
                f"site:qyyjt.cn {company} 司法",
                f"site:qyyjt.cn {company} 舆情",
                f"{company} 企业预警通 风险扫描",
                f"{company} 企业预警通 债券",
            ],
            "_urls": [
                f"{self.BASE_URL}/search?text={company}",
            ],
        }

    # ═══════════════════════════════════════════════════════
    # 内部辅助
    # ═══════════════════════════════════════════════════════

    def _build_rest_headers(self) -> Dict[str, str]:
        """新版 REST API 请求头"""
        return {
            "accept": "application/json, text/plain, */*",
            "client": "pc-web;pro",
            self.session.token_name: self.session.token_value,
            "user": self.session.user_id,
            "terminal": "pc-web;pro",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"
            ),
            "referer": f"{self.BASE_URL}/home",
            "cookie": self.session.raw_cookie,
        }

    def _build_legacy_headers(self, ep: Endpoint) -> Dict[str, str]:
        """旧版 getData.action 请求头"""
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Host": "www.qyyjt.cn",
            "Origin": self.BASE_URL,
            "PCUSS": self.session.token_value,
            "user": self.session.user_id,
            "system": "new",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
            "cookie": self.session.raw_cookie,
            "Referer": self.BASE_URL,
        }
        if ep.dataId:
            headers["dataId"] = ep.dataId
        return headers

    def _http_get(self, url: str, headers: Dict, params: Dict = None) -> Any:
        """HTTP GET with requests"""
        import requests
        return requests.get(url, headers=headers, params=params, timeout=30)

    def _http_post(self, url: str, headers: Dict, data: Dict = None) -> Any:
        """HTTP POST with requests"""
        import requests
        return requests.post(url, headers=headers, data=data, timeout=30)

    def _check_response_errors(self, data: Dict):
        """检查 API 错误码"""
        rc = data.get("returncode", data.get("code", 0))
        if rc == 104:
            raise QYJTTokenExpired("token 已过期, 需要重新登录")
        elif rc == 206:
            raise QYJTRateLimited("请求过于频繁, 请稍后再试")

    def _parse_search_result(self, data: Dict) -> Dict:
        """解析搜索结果"""
        result = {"total": 0, "list": [], "raw": data}
        inner = data.get("data", {})
        if isinstance(inner, dict):
            result["list"] = inner.get("list", [])
            result["total"] = inner.get("total", len(result["list"]))
        return result

    def _parse_bond_notices(self, data: Dict) -> Dict:
        """解析债券公告"""
        return {
            "total": len(data.get("data", [])),
            "notices": data.get("data", []),
            "raw": data,
        }

    def _token_valid(self) -> bool:
        if not self.session.token_value:
            return False
        return (self._time_provider() - self.session.login_time) < self.session.token_ttl

    def _rate_limit_check(self):
        """简单的速率限制"""
        self._request_count += 1
        if self._request_count > self._rate_limit_max:
            time.sleep(random.uniform(1, 3))
            self._request_count = 0

    def _save_session(self):
        data = {
            "token_name": self.session.token_name,
            "token_value": self.session.token_value,
            "refresh_token": self.session.refresh_token,
            "user_id": self.session.user_id,
            "raw_cookie": self.session.raw_cookie,
            "login_time": self.session.login_time,
        }
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(json.dumps(data))

    def _load_session(self):
        if self.session_path.is_file():
            try:
                data = json.loads(self.session_path.read_text())
                self.session = QYJTSession(**data)
            except Exception:
                pass

    def get_stats(self) -> dict:
        s = dict(self._stats)
        s["logged_in"] = self._token_valid()
        s["cache_size"] = len(self._cache)
        return s

    def list_endpoints(self) -> List[Dict]:
        """列出所有已知端点"""
        return [
            {
                "key": k,
                "url": e.url,
                "method": e.method,
                "api_type": e.api_type,
                "description": e.description,
            }
            for k, e in ENDPOINTS.items()
        ]


# ═══════════════════════════════════════════════════════════════
# 异常
# ═══════════════════════════════════════════════════════════════

class QYJTTokenExpired(Exception):
    pass

class QYJTRateLimited(Exception):
    pass


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

def create_adapter(session_path: str = ".wallstreet/qyyjt_session.json") -> QYJTAdapter:
    """创建默认配置的适配器"""
    return QYJTAdapter(session_path=session_path)
