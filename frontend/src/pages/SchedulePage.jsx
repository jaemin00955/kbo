import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate,useParams } from 'react-router-dom';

// 1. 구단별 아이콘 이미지 import 및 매핑 객체 생성
import kiaLogo from '../assets/logos/KIA.jpg';
import lgLogo from '../assets/logos/LG.jpg';
import ktLogo from '../assets/logos/KT.jpg';
import kiwoomLogo from '../assets/logos/키움.jpg';
import ssgLogo from '../assets/logos/SSG.jpg';
import NCLogo from '../assets/logos/NC.jpg';
import doosanLogo from '../assets/logos/두산.jpg';
import 삼성Logo from '../assets/logos/삼성.jpg';
import lotteLogo from '../assets/logos/롯데.jpg';
import hanwhaLogo from '../assets/logos/한화.jpg';

const TEAM_LOGOS = {
  'KIA': kiaLogo,
  'LG': lgLogo,
  'KT': ktLogo,
  '키움': kiwoomLogo,
  'SSG': ssgLogo,
  'NC': NCLogo,
  '두산': doosanLogo,
  '삼성': 삼성Logo,
  '롯데': lotteLogo,
  '한화': hanwhaLogo,
};

const SchedulePage = () => {
  const { date } = useParams(); // URL에서 '2026-04-22' 같은 값을 읽어옴
  const navigate = useNavigate();
  const [games, setGames] = useState([]);

  const getKboDateFormat = (d) => `${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}(${['일','월','화','수','목','금','토'][d.getDay()]})`;
  const currentDate = new Date(date);

  useEffect(() => {
    // 백엔드 API 호출 시 URL의 date 값을 그대로 사용
    // DB의 포맷에 맞게 변환하는 로직 필요 (예: 2026-04-22 -> 04.22(수))
    const formattedForApi = getKboDateFormat(currentDate); 
    axios.get(`http://localhost:8000/api/games?date=${formattedForApi}`)
         .then(res => setGames(res.data));
  }, [date]); // URL의 date가 바뀔 때마다 다시 실행

  const changeDate = (offset) => {
    const nextDate = new Date(currentDate);
    nextDate.setDate(currentDate.getDate() + offset);
    
    // 날짜를 계산한 후, 새로운 URL로 이동 (상태 변경 대신 이동!)
    const dateStr = nextDate.toISOString().split('T')[0];
    navigate(`/${dateStr}`);
  };

  return (
    <div className="app-wrapper">
      {/* 날짜 헤더 (이미지 레이아웃 재현) */}
      <header style={styles.header}>
        <button onClick={() => changeDate(-1)}>&lt;</button>
        <h2 style={styles.dateText}>{getKboDateFormat(currentDate)}</h2>
        <button onClick={() => changeDate(1)}>&gt;</button>
      </header>

      {/* 경기 리스트 (데스크탑용 Grid 레이아웃) */}
      <div style={styles.gridContainer}>
        {games.map(game => (
          <div key={game.id} style={styles.card}>
            {/* 경기 상태 및 정보 */}
            <div style={styles.cardHeader}>
              {/* <span style={styles.statusBadge}>{game.status}</span> */}
              <p style={styles.infoText}>{game.stadium} | {game.game_time}</p>
            </div>

            {/* 대진표 (아이콘 동적 삽입) */}
            <div style={styles.matchup}>
              {/* 원정 팀 */}
              <div style={styles.teamSide}>
                <img 
                  src={TEAM_LOGOS[game.away_team] || lotteLogo} // 매핑된 아이콘, 없으면 기본 로고
                  alt={`${game.away_team} 로고`} 
                  style={styles.logoImg} 
                />
                <h3 style={styles.teamName}>{game.away_team}</h3>
              </div>
              
              <div style={styles.vsText}>VS</div>

              {/* 홈 팀 */}
              <div style={styles.teamSide}>
                <img 
                  src={TEAM_LOGOS[game.home_team] || lotteLogo} 
                  alt={`${game.home_team} 로고`} 
                  style={styles.logoImg} 
                />
                <h3 style={styles.teamName}>{game.home_team}</h3>
              </div>
            </div>

            {/* 상세 분석 버튼 (이미지의 TICKET 버튼 스타일) */}
            <button 
              onClick={() => navigate(`/analysis/${game.id}`)}
              style={styles.detailBtn}
            >
              상세 분석
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- 스타일링 (이미지 완벽 재현) ---
const styles = {
  header: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '40px',
    marginBottom: '30px',
    color: '#333',
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '12px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
  },
  navBtn: {
    border: 'none',
    background: 'none',
    fontSize: '28px',
    color: '#ccc',
    cursor: 'pointer',
    padding: '0 10px'
  },
  dateText: {
    fontSize: '22px',
    fontWeight: '800',
    color: '#333',
    margin: 0
  },
  gridContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', // 카드의 최소폭을 지정하여 자동 배치
    gap: '25px'
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '12px',
    boxShadow: '0 4px 10px rgba(0,0,0,0.05)',
    overflow: 'hidden',
    transition: 'transform 0.2s'
  },
  cardHeader: {
    padding: '20px',
    textAlign: 'center',
    borderBottom: '1px solid #f0f0f0'
  },
  statusBadge: {
    display: 'inline-block',
    backgroundColor: '#e1f5fe', // 이미지의 연한 파랑 배경
    color: 'var(--kbo-blue)',   // 이미지의 진한 파랑 글씨
    padding: '5px 15px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 'bold',
    marginBottom: '10px'
  },
  infoText: {
    margin: 0,
    fontWeight: 'bold',
    fontSize: '16px',
    color: '#555'
  },
  matchup: {
    display: 'flex',
    justifyContent: 'space-around',
    alignItems: 'center',
    padding: '40px 20px',
    backgroundColor: '#fbfcfd' // 대진표 영역 미세한 배경색
  },
  teamSide: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '10px'
  },
  logoImg: {
    width: '70px',  // 이미지의 원형 로고 크기 재현
    height: '70px',
    objectFit: 'contain'
  },
  teamName: {
    color : 'black',
    margin: 0,
    fontSize: '18px',
    fontWeight: 'bold'
  },
  vsText: {
    fontSize: '20px',
    fontWeight: '900',
    color: '#ddde',
    margin: '0 20px'
  },
  detailBtn: {
    width: '100%',
    padding: '18px',
    border: 'none',
    backgroundColor: 'var(--kbo-blue)', // 공통 변수 사용
    color: '#fff',
    fontSize: '16px',
    fontWeight: 'bold',
    cursor: 'pointer',
    letterSpacing: '1px',
    textTransform: 'uppercase' // TICKET 텍스트 감성 재현
  },
};

export default SchedulePage;