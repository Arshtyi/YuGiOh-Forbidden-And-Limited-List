import json
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import html

try:
    import cloudscraper
except Exception:
    cloudscraper = None


def _build_session(headers=None, retries=3, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504)):
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
    session = _build_session(headers=headers)
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

def get_card_id(card_name):
    """
    通过ygocdb.com获取卡片ID
    """
    # 临时补丁: 替换全角尖括号为半角.https://mercury233.me/2022/01/27/%E7%99%BE%E9%B8%BD/
    if card_name:
        card_name = card_name.replace('＜', '<').replace('＞', '>')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://ygocdb.com/',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
    }
    search_url = f"https://ygocdb.com/api/v0/?search={card_name}"
    try:
        session = _build_session(headers=headers)
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and 'result' in data and len(data['result']) > 0:
            card_id = data['result'][0]['id']
            print(f"卡片 '{card_name}' 的ID: {card_id}")
            return card_id
        else:
            print(f"警告: 无法找到卡片 '{card_name}' 的ID")
            return None
    except Exception as e:
        print(f"获取卡片 '{card_name}' ID时出错: {str(e)}")
        return None

def update_md_banlist(url, output_path):
    """
    从指定URL获取Master Duel (MD)禁限卡表并更新文件
    MD的表格结构特殊,需要从每行的状态列(td[4])获取禁限级别
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://yugipedia.com/',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
    }
    print(f"正在处理Master Duel禁限卡表: {url}")
    try:
        tree = fetch_tree_with_wait(url, headers=headers,
                                    required_xpaths=["/html/body/div[3]/div[3]/div[4]/div/table[3]/tbody/tr"],
                                    timeout=15)
        table_xpath = "/html/body/div[3]/div[3]/div[4]/div/table[3]/tbody/tr"
        rows = tree.xpath(table_xpath)
        result = {
            "forbidden": [],
            "limited": [],
            "semi-limited": []
        }
        for row in rows[1:] if rows else []:
            card_name_elements = row.xpath("td[1]/a")
            if not card_name_elements:
                continue
            status_elements = row.xpath("td[4]")
            if not status_elements:
                continue
            card_name = card_name_elements[0].text.strip()
            if not card_name:
                card_name = card_name_elements[0].get("title", "").strip()
            if not card_name:
                continue
            status = status_elements[0].text.strip().lower()
            if status == "unlimited" or status == "":
                continue
            if status in ["forbidden", "limited", "semi-limited"]:
                card_id = get_card_id(card_name)
                if card_id:
                    result[status].append(card_id)
            else:
                print(f"警告: 未知的禁限状态 '{status}' 用于卡片 '{card_name}'")

        forbidden_count = len(result["forbidden"])
        limited_count = len(result["limited"])
        semi_limited_count = len(result["semi-limited"])
        total_count = forbidden_count + limited_count + semi_limited_count

        print(f"Master Duel禁限卡表统计:")
        print(f"  禁止卡片数量: {forbidden_count}")
        print(f"  限制卡片数量: {limited_count}")
        print(f"  准限制卡片数量: {semi_limited_count}")
        print(f"  总禁限卡片数量: {total_count}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"Master Duel禁限卡表已成功更新至 {output_path}")
    except Exception as e:
        print(f"更新Master Duel禁限卡表时出错: {str(e)}")

def update_banlist_with_custom_url(url, output_path):
    """
    从指定URL获取禁限卡表并更新文件
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://yugipedia.com/',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
    }
    print(f"正在处理禁限卡表链接: {url}")
    try:
        tree = fetch_tree_with_wait(url, headers=headers,
                                    required_xpaths=["/html/body/div[3]/div[3]/div[4]/div/table[1]/tbody/tr"],
                                    timeout=15)
        xpath_paths = {
            "forbidden": "/html/body/div[3]/div[3]/div[4]/div/table[1]/tbody/tr",
            "limited": "/html/body/div[3]/div[3]/div[4]/div/table[2]/tbody/tr",
            "semi-limited": "/html/body/div[3]/div[3]/div[4]/div/table[3]/tbody/tr"
        }
        result = {
            "forbidden": [],
            "limited": [],
            "semi-limited": []
        }
        for limit_type, xpath in xpath_paths.items():
            print(f"正在处理{limit_type}卡表...")
            rows = tree.xpath(xpath)
            for row in rows[1:] if rows else []:
                card_name_elements = row.xpath("td[1]/a")
                if not card_name_elements:
                    continue
                card_name = card_name_elements[0].text.strip()
                if not card_name:
                    card_name = card_name_elements[0].get("title", "").strip()
                if not card_name:
                    continue
                card_id = get_card_id(card_name)
                if card_id:
                    result[limit_type].append(card_id)

        forbidden_count = len(result["forbidden"])
        limited_count = len(result["limited"])
        semi_limited_count = len(result["semi-limited"])
        total_count = forbidden_count + limited_count + semi_limited_count

        format_name = "OCG" if "ocg" in url.lower() else "TCG" if "tcg" in url.lower() else "未知格式"

        print(f"{format_name}禁限卡表统计:")
        print(f"  禁止卡片数量: {forbidden_count}")
        print(f"  限制卡片数量: {limited_count}")
        print(f"  准限制卡片数量: {semi_limited_count}")
        print(f"  总禁限卡片数量: {total_count}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"禁限卡表已成功更新至 {output_path}")
    except Exception as e:
        print(f"更新禁限卡表时出错: {str(e)}")

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://yugipedia.com/',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
    }
    yugipedia_url = "https://yugipedia.com/wiki/Yugipedia"
    print("正在从Yugipedia首页获取最新的禁限卡表链接...")
    try:
        homepage_tree = fetch_tree_with_wait(yugipedia_url, headers=headers,
                                             required_xpaths=[
                                                 '/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[1]/a'
                                             ],
                                             timeout=15)
        tcg_link_element = homepage_tree.xpath('/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[1]/a')
        md_link_element = homepage_tree.xpath('/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[6]/a')
        ocg_link_element = homepage_tree.xpath('/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[3]/a')
        ocg_relative_url = ocg_link_element[0].get('href')
        ocg_url = f"https://yugipedia.com{ocg_relative_url}" if ocg_relative_url.startswith('/') else ocg_relative_url
        ocg_output_path = os.path.join(project_root, "res", "ocg.json")
        print(f"开始更新OCG禁限卡表...")
        update_banlist_with_custom_url(ocg_url, ocg_output_path)
        tcg_relative_url = tcg_link_element[0].get('href')
        tcg_url = f"https://yugipedia.com{tcg_relative_url}" if tcg_relative_url.startswith('/') else tcg_relative_url
        tcg_output_path = os.path.join(project_root, "res",  "tcg.json")
        print(f"开始更新TCG禁限卡表...")
        update_banlist_with_custom_url(tcg_url, tcg_output_path)
        md_relative_url = md_link_element[0].get('href')
        md_url = f"https://yugipedia.com{md_relative_url}" if md_relative_url.startswith('/') else md_relative_url
        md_output_path = os.path.join(project_root, "res",  "md.json")
        print(f"开始更新Master Duel (MD)禁限卡表...")
        update_md_banlist(md_url, md_output_path)
    except Exception as e:
        print(f"获取禁限卡表链接时出错: {str(e)}")
