from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    conn = sqlite3.connect('kbo_data.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/games")
def read_games(date: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if date:
        cursor.execute("SELECT * FROM schedule WHERE game_date = ?", (date,))
    else:
        cursor.execute("SELECT * FROM schedule")
    games = cursor.fetchall()
    conn.close()
    return [dict(game) for game in games]

@app.get("/api/game/{game_id}")
def read_game(game_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (game_id,))
    game = cursor.fetchone()
    conn.close()
    return dict(game) if game else None

@app.get("/api/roster")
def read_roster(team: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE team = ? AND is_active = 1 ORDER BY position, name", (team,))
    players = cursor.fetchall()
    conn.close()
    return [dict(player) for player in players]

# 💡 프론트엔드 통신용 데이터 모델 (ID 포함)
class PlayerInfo(BaseModel):
    name: str
    id: Optional[str] = None

class LineupRequest(BaseModel):
    team_name: str
    pitcher: PlayerInfo
    batters: List[PlayerInfo]

@app.post("/api/lineup/confirm")
async def confirm_lineup(request: LineupRequest):
    print(f"\n🚀 [{request.team_name}] 실시간 10명 크롤링 요청 수신!")
    
    # 크롤링 타겟 리스트 생성
    target_players = []
    if request.pitcher.id:
        target_players.append({"id": request.pitcher.id, "name": request.pitcher.name, "type": "P"})
        
    for batter in request.batters:
        if batter.id:
            target_players.append({"id": batter.id, "name": batter.name, "type": "B"})

    if not target_players:
        return {"status": "error", "message": "ID가 유효한 선수가 없습니다."}

    try:
        # 💡 온디맨드 실시간 크롤러 호출
        from on_demand_crawler import KBOOnDemandMiner
        miner = KBOOnDemandMiner()
        miner.crawl_players_concurrently(target_players)
        
        return {"status": "success", "message": "실시간 데이터 동기화 완료!"}
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return {"status": "error", "message": str(e)}