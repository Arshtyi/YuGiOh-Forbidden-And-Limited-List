import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import html

try:
    import cloudscraper
except Exception:
    cloudscraper = None

def build_session(headers=None, retries=3, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504)):
    """Create a requests.Session with retry strategy and default headers."""
    session = requests.Session()
    headers = headers or {}
    session.headers.update(headers)
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset(['GET', 'POST'])
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def fetch_tree_with_wait(url, headers=None, required_xpaths=None, timeout=10, interval=1):
    """
    请求 URL 并在解析为 lxml tree 后，轮询检查是否存在 required_xpaths 中的任意一个 XPath。
    如果在 timeout 秒内未出现，则抛出异常。
    使用带重试的 requests.Session；当遇到 403 Forbidden 时，如果可用会回退到 cloudscraper 来尝试获取页面。
    返回 lxml tree。
    """
    headers = headers or {}
    end_time = time.time() + timeout
    last_exception = None
    session = build_session(headers=headers)
    while True:
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 403 and cloudscraper is not None:
                try:
                    scraper = cloudscraper.create_scraper()
                    response = scraper.get(url, timeout=10)
                except Exception as cs_e:
                    raise RuntimeError(f"cloudscraper 回退失败: {cs_e}") from cs_e
            response.raise_for_status()
            tree = html.fromstring(response.content)
            if required_xpaths:
                all_missing = True
                for xp in required_xpaths:
                    found = tree.xpath(xp)
                    if found and len(found) > 0:
                        all_missing = False
                        break
                if all_missing:
                    raise RuntimeError(f"等待 XPath 出现: {required_xpaths}")
            return tree
        except Exception as e:
            last_exception = e
            if time.time() > end_time:
                raise RuntimeError(f"无法获取 {url}，最后错误: {last_exception}") from last_exception
            time.sleep(interval)
