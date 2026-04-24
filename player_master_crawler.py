import sqlite3
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class KBOMasterBuilder:
    def __init__(self):
        print("🛠️ KBO 선수 마스터 DB 구축 시작...")
        self.conn = sqlite3.connect('kbo_data.db')
        self.cursor = self.conn.cursor()
        self._setup_table()
        
        # 브라우저 백그라운드 설정
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def _setup_table(self):
        self.cursor.execute('DROP TABLE IF EXISTS players_master')
        self.cursor.execute('''
            CREATE TABLE players_master (
                player_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                team TEXT NOT NULL,
                position TEXT,       -- 'P'(투수), 'C'(포수), 'IF'(내야), 'OF'(외야)
                bats TEXT,           -- 'L'(좌타), 'R'(우타), 'S'(스위치)
                throws TEXT,         -- 'L'(좌투), 'R'(우투), 'U'(언더/사이드)
                is_active INTEGER DEFAULT 1
            )
        ''')
        self.conn.commit()
        print("✅ players_master 테이블 초기화 완료")

    def parse_bats_throws(self, hand_str):
        """ KBO의 '우언우타', '우투좌타' 등의 텍스트를 Throws/Bats로 분해 """
        throws, bats = 'R', 'R' # 기본값
        if not hand_str: return throws, bats
        
        # 투구 손 분석 (첫 2글자)
        if '좌투' in hand_str: throws = 'L'
        elif '우언' in hand_str or '우사' in hand_str or '언더' in hand_str: throws = 'U' # 언더/사이드암
        elif '우투' in hand_str: throws = 'R'
        
        # 타석 분석 (뒤 2글자)
        if '좌타' in hand_str: bats = 'L'
        elif '우타' in hand_str: bats = 'R'
        elif '양타' in hand_str: bats = 'S' # 스위치 히터
        
        return bats, throws

    def run(self):
        self.driver.get("https://www.koreabaseball.com/Player/Register.aspx")
        time.sleep(2)
        
        # 팀 로고 탭 추출
        team_tabs = self.driver.find_elements(By.CSS_SELECTOR, "div.teams ul li a")
        
        total_players = 0
        for idx in range(len(team_tabs)):
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "div.teams ul li a")
            team_name = tabs[idx].find_element(By.TAG_NAME, 'span').text.strip()
            
            # 탭 클릭
            self.driver.execute_script("arguments[0].click();", tabs[idx])
            time.sleep(1) # 표 변경 대기
            print(f"🚀 [{team_name}] 등록 선수 파싱 중...")
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 선수 등록명단에 있는 모든 테이블 가져오기
            tables = soup.find_all('table', class_='tNData')
            
            for table in tables:
                thead = table.find('thead')
                if not thead: continue
                
                # HTML 구조에서 인덱스 1번 th가 '감독', '코치', '투수', '포수', '내야수', '외야수' 중 하나임
                headers = thead.find_all('th')
                if len(headers) < 2: continue
                
                category = headers[1].text.strip()
                
                # 감독, 코치 명단은 건너뜀
                if category in ['감독', '코치']: continue
                
                # 포지션 코드 매핑
                pos_code = 'IF'
                if category == '투수': pos_code = 'P'
                elif category == '포수': pos_code = 'C'
                elif category == '외야수': pos_code = 'OF'
                
                # 선수 행(Row) 순회
                tbody = table.find('tbody')
                if not tbody: continue
                
                for row in tbody.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) < 4 or '선수가 없습니다' in cols[0].text: continue
                    
                    # cols[1] : 선수명 + 링크 (<a href="/Record/Player/PitcherDetail/Basic.aspx?playerId=64001">고영표</a>)
                    a_tag = cols[1].find('a')
                    if not a_tag: continue
                    
                    p_name = a_tag.text.strip()
                    p_id = a_tag['href'].split('playerId=')[1]
                    
                    # cols[2] : 투타유형 (ex. '우언우타')
                    hand_str = cols[2].text.strip()
                    bats, throws = self.parse_bats_throws(hand_str)
                    
                    # DB 저장
                    self.cursor.execute('''
                        INSERT OR REPLACE INTO players_master (player_id, name, team, position, bats, throws)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (p_id, p_name, team_name, pos_code, bats, throws))
                    
                    total_players += 1
            
            self.conn.commit()

        print(f"\n🎉 작업 완료! 총 {total_players}명의 선수가 마스터 DB에 초고속으로 저장되었습니다.")
        self.driver.quit()
        self.conn.close()

if __name__ == "__main__":
    builder = KBOMasterBuilder()
    builder.run()