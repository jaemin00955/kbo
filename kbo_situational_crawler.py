import sqlite3
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

class KBOSituationalMiner:
    def __init__(self):
        self.options = Options()
        self.options.add_argument("--headless") # 화면 없이 실행
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.conn = sqlite3.connect('kbo_data.db')
        self.cursor = self.conn.cursor()
        self._setup_table()

    def _setup_table(self):
        # 상황별 데이터를 통합 저장할 테이블 (타자/투수 공용)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS situational_stats (
                player_id TEXT,
                player_name TEXT,
                category TEXT,      -- '투수유형별', '주자상황별', '최근10경기', '이닝별' 등
                sub_category TEXT,  -- '좌투수', '득점권', '합계', '1회' 등
                AVG REAL, PA INTEGER, AB INTEGER, H INTEGER, HR INTEGER, BB INTEGER, SO INTEGER,
                last_updated TEXT,
                PRIMARY KEY (player_id, category, sub_category)
            )
        ''')
        self.conn.commit()

    def get_player_id(self, name, team):
        # 기존 batter_stats나 pitcher_stats에서 ID 조회
        self.cursor.execute("SELECT player_id FROM batter_stats WHERE name=? AND team=?", (name, team))
        res = self.cursor.fetchone()
        if not res:
            self.cursor.execute("SELECT player_id FROM pitcher_stats WHERE name=? AND team=?", (name, team))
            res = self.cursor.fetchone()
        return res[0] if res else None

    def extract_table_data(self, soup, title_text, is_tfoot=False):
        header = soup.find(lambda tag: tag.name in ['h5', 'h6', 'div'] and title_text in tag.text)
        if not header: return []
        table_div = header.find_next_sibling("div", class_="tbl-type02")
        if not table_div: return []
        table = table_div.find("table")
        
        headers = [th.text.strip() for th in table.find("thead").find_all("th")]
        rows = table.find("tfoot").find_all("tr") if is_tfoot else table.find("tbody").find_all("tr")
        
        results = []
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 5 or cols[0].text.strip() == "-": continue
            row_data = {"sub_category": cols[0].text.strip()}
            for i, col in enumerate(cols):
                if i == 0: continue
                val = col.text.strip().replace('-', '0')
                row_data[headers[i]] = val
            results.append(row_data)
        return results

    def crawl_player(self, player_id, is_pitcher=False):
        type_path = "PitcherDetail" if is_pitcher else "HitterDetail"
        url = f"https://www.koreabaseball.com/Record/Player/{type_path}/Basic.aspx?playerId={player_id}"
        self.driver.get(url)
        time.sleep(1)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')

        # 크롤링할 카테고리 정의
        tasks = [
            ("최근 10경기", True), 
            ("주자상황별", False),
            ("구장별", False)
        ]
        tasks.append(("타자유형별" if is_pitcher else "투수유형별", False))
        if is_pitcher: tasks.append(("이닝별", False))

        for title, is_foot in tasks:
            data_list = self.extract_table_data(soup, title, is_foot)
            for data in data_list:
                sql = '''INSERT INTO situational_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                         ON CONFLICT(player_id, category, sub_category) DO UPDATE SET AVG=excluded.AVG, PA=excluded.PA, H=excluded.H'''
                # 실제 데이터 매핑 및 저장 로직 (생략된 세부 컬럼은 파싱 데이터에 따름)
                self.cursor.execute("INSERT OR REPLACE INTO situational_stats (player_id, category, sub_category, AVG, last_updated) VALUES (?, ?, ?, ?, ?)", 
                                    (player_id, title, data['sub_category'], data.get('AVG', 0), datetime.now().strftime("%Y-%m-%d")))
        self.conn.commit()

    def close(self):
        self.driver.quit()
        self.conn.close()