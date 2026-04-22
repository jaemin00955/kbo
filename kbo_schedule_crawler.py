import sqlite3
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
##### kbo 스케쥴 크롤링 #####

# 1. SQLite 데이터베이스 및 테이블 초기화
def setup_database():
    conn = sqlite3.connect('kbo_data.db')
    cursor = conn.cursor()
    # 향후 모델링(Sabermetrics 등) 확장을 위해 홈/원정, 취소여부(status)를 세분화하여 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_year TEXT,
            game_date TEXT,
            game_time TEXT,
            away_team TEXT,
            home_team TEXT,
            stadium TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    return conn

# 2. 크롤링 세팅
def get_kbo_schedule():
    # 크롬 헤드리스 모드 (화면 안 띄우고 백그라운드 실행 시 주석 해제)
    chrome_options = Options()
    # chrome_options.add_argument("--headless") 
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # KBO 일정 페이지 접근 (URL은 실제 KBO 일정 페이지 URL로 맞춰주세요)
    url = "https://www.koreabaseball.com/Schedule/Schedule.aspx"
    driver.get(url)
    time.sleep(2) # 페이지 로딩 대기

    conn = setup_database()
    cursor = conn.cursor()

    target_year = "2026"
    target_months = ["04", "05", "06", "07", "08", "09"]

    # 연도 설정
    Select(driver.find_element(By.ID, "ddlYear")).select_by_value(target_year)
    time.sleep(1)

    for month in target_months:
        print(f"⚾ {target_year}년 {month}월 데이터 수집 중...")
        
        # 월 설정 (Select 박스 변경 시 자동으로 테이블이 비동기 로딩된다고 가정)
        Select(driver.find_element(By.ID, "ddlMonth")).select_by_value(month)
        time.sleep(2) # AJAX 로딩 대기 (필요시 WebDriverWait으로 고도화 가능)

        # 페이지 소스를 BeautifulSoup으로 파싱 (Selenium 직접 탐색보다 훨씬 빠름)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 리스트 형태의 테이블 행 추출
        rows = soup.select("#tblScheduleList tbody tr")
        
        current_date = ""
        
        for row in rows:
            tds = row.find_all('td')
            if not tds:
                continue

            # 클래스에 'day'가 있으면 첫 번째 경기 (날짜 포함)
            if tds[0].has_attr('class') and 'day' in tds[0].get('class'):
                current_date = tds[0].text.strip()
                time_idx, play_idx, stadium_idx, status_idx = 1, 2, 7, 8
            else:
                # 날짜가 없는 두 번째 경기부터는 인덱스가 하나씩 앞으로 당겨짐
                time_idx, play_idx, stadium_idx, status_idx = 0, 1, 6, 7

            # 시간
            game_time = tds[time_idx].text.strip()
            
            # 경기 (원정팀 vs 홈팀)
            play_td = tds[play_idx]
            spans = play_td.find_all('span', recursive=False) # <em> 태그 안의 점수용 span은 제외
            
            if len(spans) >= 2:
                away_team = spans[0].text.strip()
                home_team = spans[-1].text.strip()
            else:
                continue # 파싱할 수 없는 행은 건너뜀

            # 구장 및 비고(우천취소 등)
            stadium = tds[stadium_idx].text.strip()
            status = tds[status_idx].text.strip()

            # DB Insert
            cursor.execute('''
                INSERT INTO schedule (game_year, game_date, game_time, away_team, home_team, stadium, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (target_year, current_date, game_time, away_team, home_team, stadium, status))
            
    conn.commit()
    conn.close()
    driver.quit()
    print("✅ 모든 데이터 크롤링 및 SQLite 적재가 완료되었습니다!")

if __name__ == "__main__":
    get_kbo_schedule()