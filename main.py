from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# 리액트(프론트엔드)에서 접근할 수 있도록 CORS 권한 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 리액트 앱의 도메인으로 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    conn = sqlite3.connect('kbo_data.db')
    conn.row_factory = sqlite3.Row  # 컬럼명으로 데이터에 접근 가능하게 설정
    return conn

@app.get("/api/games")
def read_games(date: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 날짜(date) 파라미터가 있으면 해당 날짜 경기만, 없으면 전체 경기 반환
    if date:
        cursor.execute("SELECT * FROM schedule WHERE game_date = ?", (date,))
    else:
        cursor.execute("SELECT * FROM schedule")
        
    games = cursor.fetchall()
    conn.close()
    
    # 딕셔너리 형태로 변환하여 JSON 응답
    return [dict(game) for game in games]


@app.get("/api/game/{game_id}")
def read_game(game_id: int):
    """특정 경기 정보 가져오기 (어떤 팀끼리 붙는지 알기 위해)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (game_id,))
    game = cursor.fetchone()
    conn.close()
    return dict(game) if game else None

@app.get("/api/roster")
def read_roster(team: str):
    """특정 팀의 현재 1군 로스터 가져오기"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # is_active = 1 인 진짜 1군 선수들만 포지션별로 정렬해서 가져옴
    cursor.execute("SELECT * FROM players WHERE team = ? AND is_active = 1 ORDER BY position, name", (team,))
    players = cursor.fetchall()
    conn.close()
    return [dict(player) for player in players]