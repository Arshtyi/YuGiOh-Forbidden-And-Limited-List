from src.scrapers.base import BanlistScraper
from src.utils.network import fetch_tree_with_wait

class MasterDuelScraper(BanlistScraper):
    def scrape(self):
        print(f"正在处理Master Duel禁限卡表: {self.url}")
        try:
            tree = fetch_tree_with_wait(self.url, headers=self.headers,
                                        required_xpaths=["/html/body/div[3]/div[4]/div[4]/div/table[3]/tbody/tr"],
                                        timeout=15)
            table_xpath = "/html/body/div[3]/div[4]/div[4]/div/table[3]/tbody/tr"
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
                    card_id = self.get_card_id(card_name)
                    if card_id:
                        result[status].append(card_id)
                else:
                    print(f"警告: 未知的禁限状态 '{status}' 用于卡片 '{card_name}'")

            self.save_result(result)
        except Exception as e:
            print(f"更新Master Duel禁限卡表时出错: {str(e)}")
