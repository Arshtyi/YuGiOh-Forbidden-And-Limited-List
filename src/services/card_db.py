from src.utils.network import build_session

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
        session = build_session(headers=headers)
        response = session.get(search_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and 'result' in data and len(data['result']) > 0:
            card_id = data['result'][0]['id']
            # print(f"卡片 '{card_name}' 的ID: {card_id}") # Optional logging
            return card_id
        else:
            print(f"警告: 无法找到卡片 '{card_name}' 的ID")
            return None
    except Exception as e:
        print(f"获取卡片 '{card_name}' ID时出错: {str(e)}")
        return None
