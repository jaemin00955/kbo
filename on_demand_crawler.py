import requests
from bs4 import BeautifulSoup
import concurrent.futures
import time
import sqlite3
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class KBOOnDemandMiner:
    def __init__(self):
        # 4개의 타겟 탭 (기본, 통산, 경기별, 상황별)
        self.target_tabs = ["Basic.aspx", "Total.aspx", "Matchup.aspx", "Situation.aspx"]
        # 땅볼(GO)/뜬공(FO) 데이터를 임시로 담아둘 메모리 사전 (Dictionary)
        self.go_fo_dict = {} 
        self.setup_db()

    def setup_db(self):
        """ 프로급 DB 스키마 생성 (GO, FO 컬럼 추가됨) """
        conn = sqlite3.connect('kbo_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS situational_splits (
                player_id TEXT,
                player_name TEXT,
                player_type TEXT,    -- 'B' (타자) or 'P' (투수)
                category TEXT,       -- 'Baseline', 'Total', '상대팀별', '주자상황별' 등
                sub_category TEXT,   -- '2026', '2025', 'KIA', '득점권', '좌투수' 등
                PA_TBF INTEGER, AB INTEGER,
                H INTEGER, _2B INTEGER, _3B INTEGER, HR INTEGER,
                BB INTEGER, HBP INTEGER, SO INTEGER, GDP INTEGER,
                GO INTEGER, FO INTEGER, -- 💡 땅볼, 뜬공 컬럼 추가
                last_updated TEXT,
                PRIMARY KEY (player_id, category, sub_category)
            )
        ''')
        conn.commit()
        conn.close()

    def safe_int(self, val):
        if not val or val == '-' or val == '기록이 없습니다.': 
            return 0
        try:
            if ' ' in val: val = val.split(' ')[0] 
            return int(float(str(val).replace(',', '').strip()))
        except:
            return 0

    def parse_table_to_dicts(self, table, is_tfoot=False):
        """ KBO 테이블을 파싱하여 딕셔너리 리스트로 변환 (colspan 자동 보정) """
        if not table: return []
        
        thead = table.find('thead')
        if not thead: return []
        headers = [th.text.strip() for th in thead.find_all('th')]
        
        target_section = table.find('tfoot') if is_tfoot else table.find('tbody')
        if not target_section: return []

        results = []
        for row in target_section.find_all('tr'):
            cols = row.find_all(['th', 'td'])
            if not cols or "없습니다" in cols[0].text: continue
            
            row_data = {}
            sub_cat = "합계" if is_tfoot else cols[0].text.strip()
            row_data["sub_category"] = sub_cat
            
            col_offset = int(cols[0].get('colspan', 1)) - 1 if cols[0].has_attr('colspan') else 0
            
            col_idx = 1
            head_idx = 1 + col_offset
            
            while col_idx < len(cols) and head_idx < len(headers):
                h_name = headers[head_idx]
                row_data[h_name] = cols[col_idx].text.strip()
                head_idx += int(cols[col_idx].get('colspan', 1)) if cols[col_idx].has_attr('colspan') else 1
                col_idx += 1
                
            results.append(row_data)
            
        return results

    def preload_hitter_go_fo(self):
        """ 사용자님 제안: 깐깐한 ASP.NET 보안을 셀레니움 백그라운드 조작으로 완벽히 뚫어버립니다 """
        print("⚾ 타구 성향(GO/FO) 메모리 로딩 시작 (셀레니움 백그라운드 구동 중...)")
        
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless') # 창 안 띄우고 조용히 실행
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        try:
            driver.get("https://www.koreabaseball.com/Record/Player/HitterBasic/Detail1.aspx")
            time.sleep(1)
            
            # 1. 자바스크립트를 이용해 XBH(장타) 헤더 직접 클릭 (규정타석 필터 해제)
            driver.execute_script("sort('XBH_CN');")
            time.sleep(1.5) # 표 업데이트 대기
            
            page = 1
            while True:
                # 2. 현재 페이지의 HTML을 BeautifulSoup으로 초고속 파싱
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                extracted_in_page = 0
                
                for row in soup.find_all('tr'):
                    a_tag = row.find('a', href=True)
                    if a_tag and 'playerId=' in a_tag['href']:
                        p_id = a_tag['href'].split('playerId=')[1]
                        go_td = row.find('td', {'data-id': 'GO_CN'})
                        fo_td = row.find('td', {'data-id': 'FO_CN'})
                        
                        if go_td and fo_td:
                            self.go_fo_dict[p_id] = {
                                "GO": self.safe_int(go_td.text),
                                "FO": self.safe_int(fo_td.text)
                            }
                            extracted_in_page += 1
                            
                print(f"  - GO/FO {page}페이지 파싱 완료")
                
                # 3. 다음 페이지로 넘어가기
                page += 1
                if page > 15 or extracted_in_page == 0: 
                    break # 15페이지를 넘거나 더 이상 선수가 없으면 종료
                
                # KBO 5페이지 단위 페이징 로직 (1~5 -> 다음, 6~10 -> 다음)
                if page % 5 == 1:
                    target = 'ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ucPager$btnNext'
                else:
                    target = f'ctl00$ctl00$ctl00$cphContents$cphContents$cphContents$ucPager$btnNo{page}'
                
                # 자바스크립트로 페이지 이동 명령 전송
                driver.execute_script(f"__doPostBack('{target}','')")
                time.sleep(0.8) # 다음 페이지 로딩 대기
                
        except Exception as e:
            print(f"⚠️ 셀레니움 파싱 에러: {e}")
        finally:
            driver.quit() # 메모리 누수 방지

        print(f"⚾ 타구 성향(GO/FO) 로딩 완료! (총 {len(self.go_fo_dict)}명 확보)")

    def _extract_go_fo_from_soup(self, soup):
        """ 현재 페이지(soup)에서 선수들의 GO/FO를 찾아 사전에 넣는 함수 """
        count = 0
        for row in soup.find_all('tr'):
            a_tag = row.find('a', href=True)
            if a_tag and 'playerId=' in a_tag['href']:
                p_id = a_tag['href'].split('playerId=')[1]
                go_td = row.find('td', {'data-id': 'GO_CN'})
                fo_td = row.find('td', {'data-id': 'FO_CN'})
                if go_td and fo_td:
                    self.go_fo_dict[p_id] = {
                        "GO": self.safe_int(go_td.text), 
                        "FO": self.safe_int(fo_td.text)
                    }
                    count += 1
        return count

    def fetch_single_player(self, player):
        """ 스레드 1개가 선수 1명의 4개 탭을 순식간에 긁는 함수 """
        p_id, p_name, p_type = player["id"], player["name"], player["type"]
        path = "PitcherDetail" if p_type == 'P' else "HitterDetail"
        base_url = f"https://www.koreabaseball.com/Record/Player/{path}"
        
        extracted_data = [] 
        
        for tab in self.target_tabs:
            url = f"{base_url}/{tab}?playerId={p_id}"
            try:
                res = requests.get(url, timeout=5)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 탭 1: 기본 성적 및 최근 10경기
                if tab == "Basic.aspx":
                    h6_2026 = soup.find(lambda t: t.name == 'h6' and '2026 성적' in t.text)
                    if h6_2026:
                        divs = h6_2026.find_all_next('div', class_='tbl-type02', limit=2)
                        merged_basic = {"sub_category": "2026"}
                        for div in divs:
                            parsed = self.parse_table_to_dicts(div.find('table'))
                            if parsed: merged_basic.update(parsed[0])
                        extracted_data.append(("Baseline", merged_basic))
                    
                    h6_recent = soup.find(lambda t: t.name == 'h6' and '최근 10경기' in t.text)
                    if h6_recent:
                        recent_div = h6_recent.find_next_sibling('div', class_='tbl-type02')
                        if recent_div:
                            parsed_recent = self.parse_table_to_dicts(recent_div.find('table'), is_tfoot=True)
                            if parsed_recent: extracted_data.append(("Last_10", parsed_recent[0]))

                # 탭 2: 통산 기록 (최근 3년)
                elif tab == "Total.aspx":
                    h6_total = soup.find(lambda t: t.name == 'h6' and 'KBO 정규시즌' in t.text)
                    if h6_total:
                        total_div = h6_total.find_next_sibling('div', class_='tbl-type02')
                        if total_div:
                            parsed_total = self.parse_table_to_dicts(total_div.find('table'))
                            for row in parsed_total:
                                year = row.get('연도', '')
                                if year in ['2023', '2024', '2025']:
                                    row['sub_category'] = year
                                    extracted_data.append(("Total", row))

                # 탭 3 & 4: 상황별 스플릿
                elif tab in ["Matchup.aspx", "Situation.aspx"]:
                    categories_to_find = ["상대팀별", "구장별", "주자상황별", "이닝별", "투수유형별", "타자유형별"]
                    for cat in categories_to_find:
                        header = soup.find(lambda t: t.name == 'h5' and cat in t.text)
                        if header:
                            split_div = header.find_next_sibling('div', class_='tbl-type02')
                            if split_div:
                                parsed_splits = self.parse_table_to_dicts(split_div.find('table'))
                                for row in parsed_splits:
                                    extracted_data.append((cat, row))

            except Exception as e:
                pass
                
        time.sleep(0.05) 
        return {"id": p_id, "name": p_name, "type": p_type, "data": extracted_data}

    def crawl_players_concurrently(self, player_list):
        """ 10명 스레드 병렬 크롤링 메인 함수 """
        start_time = time.time()
        
        # 💡 본격적인 20명 파싱 시작 전, GO/FO 데이터를 메모리에 미리 로딩!
        self.preload_hitter_go_fo()
        
        print(f"⚡ 라인업 {len(player_list)}명 4개 탭 동시 정밀 스캔 시작...")
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(self.fetch_single_player, player_list)
            for res in results:
                all_results.append(res)
                
        print(f"✅ 파싱 완료! (총 소요 시간: {time.time() - start_time:.2f}초)")
        self.bulk_insert_to_db(all_results)

    def bulk_insert_to_db(self, all_results):
        """ 누락 데이터 복원 및 GO/FO 병합 후 DB 일괄 삽입 """
        conn = sqlite3.connect('kbo_data.db')
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            for player in all_results:
                p_id, p_name, p_type = player["id"], player["name"], player["type"]
                for category, d in player["data"]:
                    
                    ab = self.safe_int(d.get('AB', 0) or d.get('타수', 0))
                    h = self.safe_int(d.get('H', 0) or d.get('피안타', 0) or d.get('안타', 0))
                    d2 = self.safe_int(d.get('2B', 0))
                    d3 = self.safe_int(d.get('3B', 0))
                    hr = self.safe_int(d.get('HR', 0) or d.get('홈런', 0))
                    bb = self.safe_int(d.get('BB', 0) or d.get('4사구', 0))
                    hbp = self.safe_int(d.get('HBP', 0) or d.get('사구', 0))
                    so = self.safe_int(d.get('SO', 0) or d.get('삼진', 0))
                    gdp = self.safe_int(d.get('GDP', 0) or d.get('병살타', 0))
                    pa_tbf = self.safe_int(d.get('PA', 0) or d.get('TBF', 0) or d.get('타자', 0))

                    # 누락된 데이터 역산 로직
                    if ab == 0 and h > 0 and 'AVG' in d:
                        try:
                            avg_val = float(d['AVG'])
                            if avg_val > 0: ab = round(h / avg_val)
                        except: pass
                    
                    if pa_tbf == 0 and (ab > 0 or bb > 0 or hbp > 0):
                        pa_tbf = ab + bb + hbp
                    
                    if pa_tbf == 0: continue

                    # 💡 사용자님이 찾아낸 타자 GO/FO 데이터 병합 로직
                    go, fo = 0, 0
                    if p_type == 'B' and category == 'Baseline' and d.get('sub_category') == '2026':
                        if p_id in self.go_fo_dict:
                            go = self.go_fo_dict[p_id]["GO"]
                            fo = self.go_fo_dict[p_id]["FO"]

                    # INSERT (GO, FO 포함)
                    sql = '''
                        INSERT INTO situational_splits 
                        (player_id, player_name, player_type, category, sub_category, PA_TBF, AB, H, _2B, _3B, HR, BB, HBP, SO, GDP, GO, FO, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(player_id, category, sub_category) DO UPDATE SET 
                        PA_TBF=excluded.PA_TBF, AB=excluded.AB, H=excluded.H, _2B=excluded._2B, _3B=excluded._3B, HR=excluded.HR, 
                        BB=excluded.BB, HBP=excluded.HBP, SO=excluded.SO, GDP=excluded.GDP, 
                        GO=excluded.GO, FO=excluded.FO, last_updated=excluded.last_updated
                    '''
                    cursor.execute(sql, (p_id, p_name, p_type, category, d['sub_category'], pa_tbf, ab, h, d2, d3, hr, bb, hbp, so, gdp, go, fo, now_str))
            
            conn.commit()
            print("💾 SQLite 실시간 일괄 저장(Bulk Insert) 성공! 시뮬레이션 데이터 준비 완벽합니다!")
        except Exception as e:
            conn.rollback()
            print(f"❌ DB 저장 에러: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    # 테스트용: 강백호(B)와 고영표(P) 긁어보기
    test_players = [
        {"id": "68050", "name": "강백호", "type": "B"},
        {"id": "64001", "name": "고영표", "type": "P"}
    ]
    miner = KBOOnDemandMiner()
    miner.crawl_players_concurrently(test_players)