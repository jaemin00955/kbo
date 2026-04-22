import sqlite3
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_team_databases():
    """팀별 타자, 투수, 수비, 주루 통합 테이블을 생성합니다."""
    conn = sqlite3.connect('kbo_data.db')
    cursor = conn.cursor()
    
    # 데이터 정합성을 위해 기존 팀 테이블 초기화
    tables = ['team_batter_stats', 'team_pitcher_stats', 'team_defense_stats', 'team_runner_stats']
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    # 1. 팀 타자 테이블 (기본1 + 기본2)
    cursor.execute('''
        CREATE TABLE team_batter_stats (
            team TEXT PRIMARY KEY,
            HRA_RT REAL, GAME_CN INTEGER, PA_CN INTEGER, AB_CN INTEGER, RUN_CN INTEGER, 
            HIT_CN INTEGER, H2_CN INTEGER, H3_CN INTEGER, HR_CN INTEGER, TB_CN INTEGER, 
            RBI_CN INTEGER, SH_CN INTEGER, SF_CN INTEGER, BB_CN INTEGER, IB_CN INTEGER, 
            HP_CN INTEGER, KK_CN INTEGER, GD_CN INTEGER, SLG_RT REAL, OBP_RT REAL, 
            OPS_RT REAL, MH_HITTER_CN INTEGER, SP_HRA_RT REAL, PH_HRA_RT REAL,
            last_updated TEXT
        )
    ''')
    
    # 2. 팀 투수 테이블 (기본1 + 기본2)
    cursor.execute('''
        CREATE TABLE team_pitcher_stats (
            team TEXT PRIMARY KEY,
            ERA_RT REAL, GAME_CN INTEGER, W_CN INTEGER, L_CN INTEGER, SV_CN INTEGER, 
            HOLD_CN INTEGER, WRA_RT REAL, INN2_CN TEXT, HIT_CN INTEGER, HR_CN INTEGER, 
            BB_CN INTEGER, HP_CN INTEGER, KK_CN INTEGER, R_CN INTEGER, ER_CN INTEGER, WHIP_RT REAL,
            CG_CN INTEGER, SHO_CN INTEGER, QS_CN INTEGER, BS_CN INTEGER, PA_CN INTEGER, 
            PIT_CN INTEGER, OAVG_RT REAL, H2_CN INTEGER, H3_CN INTEGER, SH_CN INTEGER, 
            SF_CN INTEGER, IB_CN INTEGER, WP_CN INTEGER, BK_CN INTEGER,
            last_updated TEXT
        )
    ''')

    # 3. 팀 수비 테이블
    cursor.execute('''
        CREATE TABLE team_defense_stats (
            team TEXT PRIMARY KEY,
            GAME_CN INTEGER, ERR_CN INTEGER, POFF_CN INTEGER, PO_CN INTEGER, 
            ASS_CN INTEGER, GDP_CN INTEGER, FPCT_RT REAL, PB_CN INTEGER, 
            SB_CN INTEGER, CS_CN INTEGER, CS_RT REAL, last_updated TEXT
        )
    ''')

    # 4. 팀 주루 테이블
    cursor.execute('''
        CREATE TABLE team_runner_stats (
            team TEXT PRIMARY KEY,
            GAME_CN INTEGER, SBA_CN INTEGER, SB_CN INTEGER, CS_CN INTEGER, 
            SB_RT REAL, RO_CN INTEGER, POFF_CN INTEGER, last_updated TEXT
        )
    ''')

    conn.commit()
    return conn

class KBOTeamMasterMiner:
    def __init__(self):
        print("🤖 팀 통합 마스터 크롤러 가동 준비 중...")
        self.options = Options()
        self.options.add_argument("--headless") # 백그라운드 실행
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.conn = setup_team_databases() 
        self.conn.row_factory = sqlite3.Row

    def parse_and_save(self, table_name):
        """현재 페이지의 팀 표를 읽어 DB에 UPSERT 합니다."""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        table = soup.select_one(".tData.tt")
        if not table: return

        rows = table.select("tbody tr")
        cursor = self.conn.cursor()
        
        for row in rows:
            tds = row.select("td")
            if len(tds) < 3: continue # 빈 줄 패스
            
            team_name = tds[1].text.strip()
            data = {"team": team_name, "last_updated": datetime.now().strftime("%Y-%m-%d")}
            
            for td in tds:
                col_name = td.get('data-id')
                if not col_name: continue
                
                # 데이터 정제: '-'는 0으로, 그 외엔 텍스트 유지 (SQL이 타입에 맞춰 처리)
                val = td.text.strip().replace('-', '0')
                data[col_name] = val

            # 동적 SQL 생성 (UPSERT)
            cols = ', '.join(f'"{k}"' for k in data.keys())
            placeholders = ', '.join(['?'] * len(data))
            sql = f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT(team) DO UPDATE SET '
            sql += ', '.join([f'"{k}"=excluded."{k}"' for k in data.keys() if k != "team"])
            
            cursor.execute(sql, list(data.values()))
        self.conn.commit()

    def run(self):
        # 탭별 URL 및 저장할 테이블 매핑
        tasks = [
            ("타자 기본 1", "https://www.koreabaseball.com/Record/Team/Hitter/Basic1.aspx", "team_batter_stats"),
            ("타자 기본 2", "https://www.koreabaseball.com/Record/Team/Hitter/Basic2.aspx", "team_batter_stats"),
            ("투수 기본 1", "https://www.koreabaseball.com/Record/Team/Pitcher/Basic1.aspx", "team_pitcher_stats"),
            ("투수 기본 2", "https://www.koreabaseball.com/Record/Team/Pitcher/Basic2.aspx", "team_pitcher_stats"),
            ("수비 기록", "https://www.koreabaseball.com/Record/Team/Defense/Basic.aspx", "team_defense_stats"),
            ("주루 기록", "https://www.koreabaseball.com/Record/Team/Runner/Basic.aspx", "team_runner_stats")
        ]
        
        for name, url, table in tasks:
            print(f"👉 [{name}] 수집 중...")
            self.driver.get(url)
            time.sleep(2)
            self.parse_and_save(table)

        print("\n🎉 모든 팀 스탯이 통합 데이터베이스에 성공적으로 저장되었습니다!")
        self.driver.quit()
        self.conn.close()

if __name__ == "__main__":
    miner = KBOTeamMasterMiner()
    miner.run()