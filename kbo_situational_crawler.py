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
        self.options.add_argument("--headless") # 백그라운드 실행
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.conn = sqlite3.connect('kbo_data.db')
        self.cursor = self.conn.cursor()
        self._setup_table()

    def _setup_table(self):
        # 기존 테이블을 날리고 타자/투수 통합 테이블로 새로 생성합니다.
        self.cursor.execute('DROP TABLE IF EXISTS situational_stats')
        self.cursor.execute('''
            CREATE TABLE situational_stats (
                player_id TEXT,
                player_name TEXT,
                player_type TEXT,    -- 'Hitter' or 'Pitcher'
                category TEXT,       -- '최근 10경기', '상대팀별', '주자상황별' 등
                sub_category TEXT,   -- '합계', '좌투수', '득점권', '잠실' 등
                AVG REAL, PA INTEGER, AB INTEGER,       -- 타자용 스탯 (투수는 피안타율)
                ERA REAL, IP TEXT, TBF INTEGER,         -- 투수용 스탯 (평균자책점, 이닝, 타자수)
                H INTEGER, HR INTEGER, BB INTEGER, SO INTEGER, -- 공통 스탯
                last_updated TEXT,
                PRIMARY KEY (player_id, category, sub_category)
            )
        ''')
        self.conn.commit()

    def get_player_id(self, name, team):
        # 타자 테이블에서 찾기
        self.cursor.execute("SELECT player_id FROM batter_stats WHERE name=? AND team=?", (name, team))
        res = self.cursor.fetchone()
        if res: return res[0], 'Hitter'
        
        # 투수 테이블에서 찾기
        self.cursor.execute("SELECT player_id FROM pitcher_stats WHERE name=? AND team=?", (name, team))
        res = self.cursor.fetchone()
        if res: return res[0], 'Pitcher'
        
        return None, None

    def safe_float(self, val):
        try: return float(val.replace('-', '0').strip())
        except: return 0.0

    def safe_int(self, val):
        try: return int(val.replace('-', '0').strip())
        except: return 0

    def extract_table(self, soup, keyword, is_tfoot=False):
        """colspan을 동적으로 계산하여 타자/투수 상관없이 정확히 컬럼을 매핑합니다."""
        table = soup.find('table', {'summary': lambda x: x and keyword in x})
        if not table:
            # h5, h6 등의 제목으로 탐색
            h_tag = soup.find(lambda tag: tag.name in ['h5', 'h6', 'div'] and keyword in tag.text)
            if h_tag:
                table_div = h_tag.find_next_sibling('div', class_='tbl-type02')
                if table_div: table = table_div.find('table')
        if not table: return []

        thead = table.find('thead')
        if not thead: return []
        headers = [th.text.strip() for th in thead.find_all('th')]

        target_rows = []
        if is_tfoot and table.find('tfoot'):
            target_rows = table.find('tfoot').find_all('tr')
        elif not is_tfoot and table.find('tbody'):
            target_rows = table.find('tbody').find_all('tr')

        results = []
        for row in target_rows:
            cols = row.find_all(['th', 'td'])
            if not cols: continue
            
            sub_cat = cols[0].text.strip()
            if sub_cat in ["-", "기록이 없습니다."]: continue

            # 💡 [핵심 로직] 합계 부분의 colspan 값(타자:2, 투수:3)을 추출하여 헤더 인덱스를 보정합니다.
            col_offset = 0
            if cols[0].has_attr('colspan'):
                col_offset = int(cols[0]['colspan']) - 1

            row_data = {"sub_category": sub_cat if not is_tfoot else "합계"}
            
            col_idx = 1
            head_idx = 1 + col_offset
            
            # 남은 컬럼들을 헤더와 1:1로 매칭
            while col_idx < len(cols) and head_idx < len(headers):
                h_name = headers[head_idx]
                row_data[h_name] = cols[col_idx].text.strip()
                
                # 혹시 현재 데이터 셀도 colspan이 있다면 헤더 인덱스를 더 뜀
                if cols[col_idx].has_attr('colspan'):
                    head_idx += int(cols[col_idx]['colspan'])
                else:
                    head_idx += 1
                col_idx += 1
                    
            results.append(row_data)
        return results

    def crawl_player(self, p_id, p_name, p_type):
        base_url = "https://www.koreabaseball.com/Record/Player/"
        path = "PitcherDetail" if p_type == 'Pitcher' else "HitterDetail"
        
        # 1. 기본 탭 (최근 10경기)
        self.driver.get(f"{base_url}{path}/Basic.aspx?playerId={p_id}")
        time.sleep(0.5)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        self.save_to_db(p_id, p_name, p_type, "최근 10경기", self.extract_table(soup, "최근 10경기", is_tfoot=True))

        # 2. 경기별 기록 탭 (상대팀별, 구장별, 홈/방문별)
        self.driver.get(f"{base_url}{path}/Matchup.aspx?playerId={p_id}")
        time.sleep(0.5)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        self.save_to_db(p_id, p_name, p_type, "상대팀별", self.extract_table(soup, "상대팀별"))
        self.save_to_db(p_id, p_name, p_type, "구장별", self.extract_table(soup, "구장별"))
        self.save_to_db(p_id, p_name, p_type, "홈/방문별", self.extract_table(soup, "홈/방문별"))

        # 3. 상황별 기록 탭 (주자상황별, 이닝별, 아웃카운트별, 투수/타자유형별)
        self.driver.get(f"{base_url}{path}/Situation.aspx?playerId={p_id}")
        time.sleep(0.5)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        self.save_to_db(p_id, p_name, p_type, "주자상황별", self.extract_table(soup, "주자상황별"))
        self.save_to_db(p_id, p_name, p_type, "이닝별", self.extract_table(soup, "이닝별"))
        self.save_to_db(p_id, p_name, p_type, "아웃카운트별", self.extract_table(soup, "아웃카운트별"))
        
        # 타자는 투수유형별 / 투수는 타자유형별
        vs_type = "타자유형별" if p_type == 'Pitcher' else "투수유형별"
        self.save_to_db(p_id, p_name, p_type, vs_type, self.extract_table(soup, vs_type))

    def save_to_db(self, p_id, p_name, p_type, category, data_list):
        for d in data_list:
            if not d: continue
            
            # get을 통해 가져오되, 값이 없으면 0으로 기본값 세팅
            avg = self.safe_float(d.get('AVG', '0'))
            era = self.safe_float(d.get('ERA', '0'))
            pa  = self.safe_int(d.get('PA', '0'))
            ab  = self.safe_int(d.get('AB', '0'))
            tbf = self.safe_int(d.get('TBF', '0'))
            ip  = d.get('IP', '0').replace('-', '0') # 이닝은 텍스트 그대로
            h   = self.safe_int(d.get('H', '0'))
            hr  = self.safe_int(d.get('HR', '0'))
            bb  = self.safe_int(d.get('BB', '0'))
            so  = self.safe_int(d.get('SO', '0'))

            sql = '''
                INSERT INTO situational_stats 
                (player_id, player_name, player_type, category, sub_category, AVG, PA, AB, ERA, IP, TBF, H, HR, BB, SO, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id, category, sub_category) DO UPDATE SET 
                AVG=excluded.AVG, PA=excluded.PA, AB=excluded.AB, ERA=excluded.ERA, IP=excluded.IP, TBF=excluded.TBF, H=excluded.H, HR=excluded.HR, BB=excluded.BB, SO=excluded.SO, last_updated=excluded.last_updated
            '''
            self.cursor.execute(sql, (p_id, p_name, p_type, category, d['sub_category'], avg, pa, ab, era, ip, tbf, h, hr, bb, so, datetime.now().strftime("%Y-%m-%d")))
        self.conn.commit()

    def close(self):
        self.driver.quit()
        self.conn.close()