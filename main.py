from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from kbo_situational_crawler import KBOSituationalMiner

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

class LineupRequest(BaseModel):
    pitcher_name: str
    batter_names: list[str]

@app.post("/api/simulate")
async def run_simulation(request: LineupRequest):
    print(f"🔥 라인업 확정됨! 실시간 디테일 크롤링 시작...")
    
    # 1. 상황별 데이터 실시간 크롤링 및 DB 저장
    miner = KBOSituationalMiner()
    # 타자들의 디테일 데이터를 긁고 결과를 받아옴 (투수도 필요하다면 추후 로직 추가)
    situational_results = miner.process_lineup(request.batter_names)
    miner.close()
    
    print("✅ 크롤링 및 DB 저장 완료. 결과를 클라이언트로 전송합니다.")

    # 2. React로 결과 반환
    # 나중에는 여기에 situational_results를 바탕으로 Log5 확률 계산 로직이 들어갑니다.
    return {
        "message": "시뮬레이션 데이터 준비 완료",
        "pitcher": request.pitcher_name,
        "matchup_details": situational_results
    }

@app.post("/api/lineup/confirm")
async def confirm_lineup(request: LineupRequest):
    print(f"🚀 라인업 확정 요청 수신: 투수-{request.pitcher_name}, 타자-{len(request.batter_names)}명")
    
    # 크롤러 가동
    miner = KBOSituationalMiner()
    try:
        # 1. 투수 상세 데이터 크롤링 (팀명 정보가 필요하므로 프론트에서 같이 보내주면 좋습니다)
        # 우선 이름으로 ID를 찾는 로직이 내부에 있어야 합니다.
        p_id = miner.get_player_id(request.pitcher_name)
        if p_id:
            miner.crawl_player(p_id, is_pitcher=True)

        # 2. 타자 1~9번 상세 데이터 크롤링
        for b_name in request.batter_names:
            b_id = miner.get_player_id(b_name)
            if b_id:
                miner.crawl_player(b_id, is_pitcher=False)
            
        return {"status": "success", "message": "상세 데이터 동기화 완료!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        miner.close()