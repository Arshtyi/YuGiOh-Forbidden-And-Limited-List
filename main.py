import os
from src.utils.network import fetch_tree_with_wait
from src.scrapers.master_duel import MasterDuelScraper
from src.scrapers.ocg_tcg import OcgTcgScraper

def main():
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
        
        # OCG
        ocg_link_element = homepage_tree.xpath('/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[3]/a')
        ocg_relative_url = ocg_link_element[0].get('href')
        ocg_url = f"https://yugipedia.com{ocg_relative_url}" if ocg_relative_url.startswith('/') else ocg_relative_url
        ocg_output_path = os.path.join(project_root, "res", "ocg.json")
        print(f"开始更新OCG禁限卡表...")
        OcgTcgScraper(ocg_url, ocg_output_path).scrape()

        # TCG
        tcg_link_element = homepage_tree.xpath('/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[1]/a')
        tcg_relative_url = tcg_link_element[0].get('href')
        tcg_url = f"https://yugipedia.com{tcg_relative_url}" if tcg_relative_url.startswith('/') else tcg_relative_url
        tcg_output_path = os.path.join(project_root, "res",  "tcg.json")
        print(f"开始更新TCG禁限卡表...")
        OcgTcgScraper(tcg_url, tcg_output_path).scrape()

        # Master Duel
        md_link_element = homepage_tree.xpath('/html/body/div[3]/div[4]/div[4]/div/div[1]/div[3]/div[1]/ul/li[6]/a')
        md_relative_url = md_link_element[0].get('href')
        md_url = f"https://yugipedia.com{md_relative_url}" if md_relative_url.startswith('/') else md_relative_url
        md_output_path = os.path.join(project_root, "res",  "md.json")
        print(f"开始更新Master Duel (MD)禁限卡表...")
        MasterDuelScraper(md_url, md_output_path).scrape()

    except Exception as e:
        print(f"获取禁限卡表链接时出错: {str(e)}")

if __name__ == "__main__":
    main()
