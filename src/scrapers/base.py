import json
import os
from abc import ABC, abstractmethod
from src.utils.network import fetch_tree_with_wait
from src.services.card_db import get_card_id

class BanlistScraper(ABC):
    def __init__(self, url, output_path):
        self.url = url
        self.output_path = output_path
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://yugipedia.com/',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }

    @abstractmethod
    def scrape(self):
        pass

    def save_result(self, result):
        forbidden_count = len(result["forbidden"])
        limited_count = len(result["limited"])
        semi_limited_count = len(result["semi-limited"])
        total_count = forbidden_count + limited_count + semi_limited_count

        print(f"统计信息 ({self.output_path}):")
        print(f"  禁止卡片数量: {forbidden_count}")
        print(f"  限制卡片数量: {limited_count}")
        print(f"  准限制卡片数量: {semi_limited_count}")
        print(f"  总禁限卡片数量: {total_count}")

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        print(f"禁限卡表已成功更新至 {self.output_path}")

    def get_card_id(self, card_name):
        return get_card_id(card_name)
