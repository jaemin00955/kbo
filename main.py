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
    team_name: str         
    pitcher_name: str
    batter_names: list[str]

@app.post("/api/simulate")
async def run_simulation(request: LineupRequest):
    print(f"🔥 라인업 분석(Log5 시뮬레이션) 시작...")
    # TODO: 다음 단계에서 여기에 DB 데이터를 불러와 Log5 수학 엔진을 돌리는 코드를 작성할 예정입니다.
    return {
        "message": "시뮬레이션 로직 준비 중",
        "pitcher": request.pitcher_name,
        "matchup_details": []
    }

@app.post("/api/lineup/confirm")
async def confirm_lineup(request: LineupRequest):
    print(f"\n🚀 [{request.team_name}] 라인업 확정 요청 수신: 투수-{request.pitcher_name}, 타자-{len(request.batter_names)}명")
    
    # 크롤러 가동
    miner = KBOSituationalMiner()
    try:
        # 💡 2. 투수/타자를 한 번에 묶어서 처리하도록 로직을 깔끔하게 개선
        all_players = []
        if request.pitcher_name: 
            all_players.append(request.pitcher_name)
        # 타자 리스트에서 빈 이름(선택 안 됨)은 제외하고 추가
        all_players.extend([name for name in request.batter_names if name])

        for p_name in all_players:
            # 💡 3. 바뀐 크롤러 함수 사용법 적용 (팀명을 넘겨서 ID와 선수 유형(투/타)을 정확히 받아옴)
            p_id, p_type = miner.get_player_id(p_name, request.team_name)
            
            if p_id:
                print(f"  👉 {p_type} [{p_name}] 상세 데이터 크롤링 중 (3개 탭 순회)...")
                miner.crawl_player(p_id, p_name, p_type)
            else:
                print(f"  ⚠️ [{p_name}] 선수를 DB에서 찾을 수 없습니다.")
            
        return {"status": "success", "message": "상세 데이터 동기화 완료!"}
    
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        miner.close()