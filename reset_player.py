import sqlite3

# DB 연결
conn = sqlite3.connect('kbo_data.db')
cursor = conn.cursor()

# players 테이블만 삭제 (일정 데이터는 안전함!)
cursor.execute("DROP TABLE IF EXISTS players")
conn.commit()
conn.close()

print("✅ players 테이블이 초기화되었습니다. 이제 크롤러를 다시 실행해 보세요!")