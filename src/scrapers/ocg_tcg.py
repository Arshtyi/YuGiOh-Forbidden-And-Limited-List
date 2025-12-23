from src.scrapers.base import BanlistScraper
from src.utils.network import fetch_tree_with_wait

class OcgTcgScraper(BanlistScraper):
    def scrape(self):
        print(f"正在处理禁限卡表链接: {self.url}")
        try:
            tree = fetch_tree_with_wait(self.url, headers=self.headers,
                                        required_xpaths=["/html/body/div[3]/div[4]/div[4]/div/table[1]/tbody"],
                                        timeout=15)
            xpath_paths = {
                "forbidden": "/html/body/div[3]/div[4]/div[4]/div/table[1]/tbody/tr",
                "limited": "/html/body/div[3]/div[4]/div[4]/div/table[2]/tbody/tr",
                "semi-limited": "/html/body/div[3]/div[4]/div[4]/div/table[3]/tbody/tr"
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
                    card_id = self.get_card_id(card_name)
                    if card_id:
                        result[limit_type].append(card_id)

            self.save_result(result)
        except Exception as e:
            print(f"更新禁限卡表时出错: {str(e)}")
