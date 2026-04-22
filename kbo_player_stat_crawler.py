import sqlite3
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_player_databases():
    """선수별 타자, 투수, 수비, 주루 통합 테이블을 한 번에 생성합니다."""
    conn = sqlite3.connect('kbo_data.db')
    cursor = conn.cursor()
    
    # 꼬임 방지를 위해 기존 테이블 날리기
    tables = ['batter_stats', 'pitcher_stats', 'defense_stats', 'runner_stats']
    for table in tables:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    # 1. 타자 마스터 테이블
    cursor.execute('''
        CREATE TABLE batter_stats (
            player_id TEXT PRIMARY KEY, name TEXT, team TEXT,
            HRA_RT REAL, GAME_CN INTEGER, PA_CN INTEGER, AB_CN INTEGER, RUN_CN INTEGER, 
            HIT_CN INTEGER, H2_CN INTEGER, H3_CN INTEGER, HR_CN INTEGER, TB_CN INTEGER, 
            RBI_CN INTEGER, SH_CN INTEGER, SF_CN INTEGER, BB_CN INTEGER, IB_CN INTEGER, 
            HP_CN INTEGER, KK_CN INTEGER, GD_CN INTEGER, SLG_RT REAL, OBP_RT REAL, 
            OPS_RT REAL, MH_HITTER_CN INTEGER, SP_HRA_RT REAL, PH_HRA_RT REAL,
            XBH_CN INTEGER, GO_CN INTEGER, FO_CN INTEGER, FOGO_RT REAL, WIN_HIT_CN INTEGER, 
            KK_BB_RT REAL, PA_PIT_RT REAL, ISO_RT REAL, XR_RT REAL, GPA_RT REAL,
            last_updated TEXT
        )
    ''')
    
    # 2. 투수 마스터 테이블
    cursor.execute('''
        CREATE TABLE pitcher_stats (
            player_id TEXT PRIMARY KEY, name TEXT, team TEXT,
            ERA_RT REAL, GAME_CN INTEGER, W_CN INTEGER, L_CN INTEGER, SV_CN INTEGER, 
            HOLD_CN INTEGER, WRA_RT REAL, INN2_CN TEXT, HIT_CN INTEGER, HR_CN INTEGER, 
            BB_CN INTEGER, HP_CN INTEGER, KK_CN INTEGER, R_CN INTEGER, ER_CN INTEGER, WHIP_RT REAL,
            CG_CN INTEGER, SHO_CN INTEGER, QS_CN INTEGER, BS_CN INTEGER, PA_CN INTEGER, 
            PIT_CN INTEGER, OAVG_RT REAL, H2_CN INTEGER, H3_CN INTEGER, SH_CN INTEGER, 
            SF_CN INTEGER, IB_CN INTEGER, WP_CN INTEGER, BK_CN INTEGER, START_CN INTEGER, 
            START_W_CN INTEGER, RELIEF_W_CN INTEGER, QUIT_CN INTEGER, SVO_CN INTEGER, 
            TS_CN INTEGER, GD_CN INTEGER, GO_CN INTEGER, FO_CN INTEGER, FOGO_RT REAL,
            BABIP_RT REAL, GAME_PIT_AVG_RT REAL, INN_PIT_AVG_RT REAL, GAME_KK_RT REAL, 
            GAME_BB_RT REAL, BB_KK_RT REAL, OOBP_RT REAL, OSLG_RT REAL, OOPS_RT REAL,
            last_updated TEXT
        )
    ''')

    # 3. 수비 마스터 테이블
    cursor.execute('''
        CREATE TABLE defense_stats (
            player_id TEXT PRIMARY KEY, name TEXT, team TEXT,
            POS_SC TEXT, GAME_CN INTEGER, START_GAME_CN INTEGER, DEFEN_INN2_CN TEXT, 
            ERR_CN INTEGER, POFF_CN INTEGER, PO_CN INTEGER, ASS_CN INTEGER, 
            GDP_CN INTEGER, FPCT_RT REAL, PB_CN INTEGER, SB_CN INTEGER, 
            CS_CN INTEGER, CS_RT REAL, last_updated TEXT
        )
    ''')

    # 4. 주루 마스터 테이블
    cursor.execute('''
        CREATE TABLE runner_stats (
            player_id TEXT PRIMARY KEY, name TEXT, team TEXT,
            GAME_CN INTEGER, SBA_CN INTEGER, SB_CN INTEGER, CS_CN INTEGER, 
            SB_RT REAL, RO_CN INTEGER, POFF_CN INTEGER, last_updated TEXT
        )
    ''')

    conn.commit()
    return conn

class KBOPlayerMasterMiner:
    def __init__(self):
        print("🤖 선수 스탯 통합 마이닝 브라우저 세팅 중 (시간이 조금 걸릴 수 있습니다)...")
        self.options = Options()
        self.options.add_argument("--headless") # 선수 크롤링은 양이 많아 무조건 백그라운드 권장
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        self.conn = setup_player_databases() 
        self.conn.row_factory = sqlite3.Row

    def parse_and_save(self, table_name):
        """현재 화면의 표를 파싱하여 지정된 DB 테이블에 UPSERT"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        table = soup.select_one(".tData01.tt")
        if not table: return

        rows = table.select("tbody tr")
        cursor = self.conn.cursor()
        
        for row in rows:
            tds = row.select("td")
            if len(tds) < 5: continue
            
            try:
                player_link = tds[1].find("a")['href']
                player_id = player_link.split("playerId=")[1]
            except:
                continue

            data = {
                "player_id": player_id, 
                "name": tds[1].text.strip(), 
                "team": tds[2].text.strip(), 
                "last_updated": datetime.now().strftime("%Y-%m-%d")
            }
            
            for i, td in enumerate(tds):
                if i < 3: continue
                col_name = td.get('data-id')
                if not col_name: continue
                
                # '-' 표시는 0으로 변환
                val = td.text.strip().replace('-', '0')
                data[col_name] = val

            cols = ', '.join(f'"{k}"' for k in data.keys())
            placeholders = ', '.join(['?'] * len(data))
            sql = f'INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT(player_id) DO UPDATE SET '
            sql += ', '.join([f'"{k}"=excluded."{k}"' for k in data.keys() if k != "player_id"])
            
            try:
                cursor.execute(sql, list(data.values()))
            except sqlite3.OperationalError as e:
                pass # 미등록 컬럼 조용히 스킵
                
        self.conn.commit()

    def crawl_team_pages(self, url, team_value, team_name, table_name):
        """특정 탭에서 1개 구단을 선택하고 페이지를 순회하며 크롤링"""
        self.driver.get(url)
        time.sleep(1.5)
        
        try:
            # 팀 선택 드롭다운 (규정 이닝/타석 필터 해제용)
            team_dropdown = Select(self.driver.find_element(By.ID, "cphContents_cphContents_cphContents_ddlTeam_ddlTeam"))
            team_dropdown.select_by_value(team_value)
            time.sleep(2) 
        except Exception as e:
            return

        page = 1
        while True:
            self.parse_and_save(table_name)
            
            try:
                next_page_num = page + 1
                btn_id = f"cphContents_cphContents_cphContents_ucPager_btnNo{next_page_num}"
                next_btn = self.driver.find_element(By.ID, btn_id)
                
                if "on" not in next_btn.get_attribute("class"):
                    next_btn.click()
                    time.sleep(1.5)
                    page += 1
                else:
                    break
            except:
                break

    def run(self):
        # 긁어야 할 모든 탭 URL (총 9개) 및 대상 테이블 매핑
        tasks = [
            ("타자 기본 1", "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic1.aspx", "batter_stats"),
            ("타자 기본 2", "https://www.koreabaseball.com/Record/Player/HitterBasic/Basic2.aspx", "batter_stats"),
            ("타자 세부 1", "https://www.koreabaseball.com/Record/Player/HitterBasic/Detail1.aspx", "batter_stats"),
            ("투수 기본 1", "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic1.aspx", "pitcher_stats"),
            ("투수 기본 2", "https://www.koreabaseball.com/Record/Player/PitcherBasic/Basic2.aspx", "pitcher_stats"),
            ("투수 세부 1", "https://www.koreabaseball.com/Record/Player/PitcherBasic/Detail1.aspx", "pitcher_stats"),
            ("투수 세부 2", "https://www.koreabaseball.com/Record/Player/PitcherBasic/Detail2.aspx", "pitcher_stats"),
            ("수비 기록", "https://www.koreabaseball.com/Record/Player/Defense/Basic.aspx", "defense_stats"),
            ("주루 기록", "https://www.koreabaseball.com/Record/Player/Runner/Basic.aspx", "runner_stats")
        ]
        
        teams = [
            ("KT", "KT"), ("LG", "LG"), ("SS", "삼성"), ("SK", "SSG"), 
            ("HT", "KIA"), ("OB", "두산"), ("HH", "한화"), ("NC", "NC"), 
            ("WO", "키움"), ("LT", "롯데")
        ]

        print("\n🚀 데이터 파이프라인 가동! (약 3~5분 정도 소요됩니다)")
        
        # 9개의 탭을 순회
        for tab_name, url, table_name in tasks:
            print(f"\n🌐 [{tab_name}] 수집 중...")
            # 각 탭에서 10개 구단을 순회
            for team_value, team_name in teams:
                # 진행률 표시를 위해 print 시 end="\r" 사용
                print(f"  👉 {team_name} 처리 중...{' ' * 20}", end="\r")
                self.crawl_team_pages(url, team_value, team_name, table_name)
            print(f"  ✅ [{tab_name}] 10개 구단 수집 완료!{' ' * 10}")

        print("\n🎉 KBO 전체 선수(타/투/수/주) 마스터 데이터베이스 구축 완료!")
        self.driver.quit()
        self.conn.close()

if __name__ == "__main__":
    miner = KBOPlayerMasterMiner()
    miner.run()