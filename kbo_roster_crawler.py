import sqlite3
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import re

def setup_database():
    conn = sqlite3.connect('kbo_data.db')
    cursor = conn.cursor()
    # back_number 제외하고 원래 구조로 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT,
            name TEXT,
            position TEXT,
            is_active INTEGER,
            last_updated TEXT,
            UNIQUE(team, name)
        )
    ''')
    conn.commit()
    return conn

def extract_clean_name(text):
    """'고영표(1)' 형태의 텍스트에서 괄호를 지우고 이름만 추출"""
    match = re.match(r"([가-힣a-zA-Z]+)\(", text.strip())
    if match:
        return match.group(1) # 괄호 앞의 이름만 반환
    return text.strip()

def crawl_kbo_all_roster():
    print("⚾ KBO 1군 전체 로스터 크롤링을 시작합니다...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    url = "https://www.koreabaseball.com/Player/RegisterAll.aspx"
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    conn = setup_database()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE players SET is_active = 0")
    today_str = datetime.now().strftime("%Y-%m-%d")

    team_tables = soup.find_all("table", class_="tData tDays")

    for table in team_tables:
        tbody = table.find("tbody")
        if not tbody: continue
        
        tr = tbody.find("tr")
        tds = tr.find_all(["th", "td"])
        
        if len(tds) < 7: continue
        
        team_cell_text = tds[0].get_text(separator="|").split("|")
        team_name = team_cell_text[0].strip()
        
        positions_map = {
            3: "투수",
            4: "포수",
            5: "내야수",
            6: "외야수"
        }
        
        print(f"[{team_name}] 데이터 파싱 중...")
        
        for idx, position_name in positions_map.items():
            ul = tds[idx].find("ul")
            if not ul: continue
            
            lis = ul.find_all("li")
            for li in lis:
                raw_text = li.text.strip()
                if not raw_text: continue
                
                # 깔끔하게 이름만 추출
                clean_name = extract_clean_name(raw_text)
                
                cursor.execute('''
                    INSERT INTO players (team, name, position, is_active, last_updated)
                    VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(team, name) 
                    DO UPDATE SET is_active=1, position=excluded.position, last_updated=excluded.last_updated
                ''', (team_name, clean_name, position_name, today_str))

    conn.commit()
    conn.close()
    driver.quit()
    print("✅ 모든 구단의 1군 로스터 수집 및 업데이트가 완료되었습니다!")

if __name__ == "__main__":
    crawl_kbo_all_roster()