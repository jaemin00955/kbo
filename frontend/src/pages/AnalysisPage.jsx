import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const POSITIONS = ['투수(P)', '포수(C)', '1루수(1B)', '2루수(2B)', '3루수(3B)', '유격수(SS)', '좌익수(LF)', '중견수(CF)', '우익수(RF)', '지명타자(DH)'];

const AnalysisPage = () => {
  const { gameId } = useParams();
  const navigate = useNavigate();
  
  const [gameInfo, setGameInfo] = useState(null);
  const [awayRoster, setAwayRoster] = useState([]);
  const [homeRoster, setHomeRoster] = useState([]);
  
  const [crawlStatus, setCrawlStatus] = useState({ away: 'idle', home: 'idle' });

  const [lineups, setLineups] = useState({
    away: { 1: { pos: '중견수(CF)', name: '이진영' }, 2: { pos: '우익수(RF)', name: '페라자' }, 3: { pos: '3루수(3B)', name: '노시환' }, 4: { pos: '1루수(1B)', name: '채은성' }, 5: { pos: '지명타자(DH)', name: '안치홍' }, 6: { pos: '2루수(2B)', name: '문현빈' }, 7: { pos: '유격수(SS)', name: '이도윤' }, 8: { pos: '포수(C)', name: '최재훈' }, 9: { pos: '좌익수(LF)', name: '최인호' }, 'P': { pos: '투수(P)', name: '류현진' } },
    home: { 1: { pos: '우익수(RF)', name: '홍창기' }, 2: { pos: '중견수(CF)', name: '박해민' }, 3: { pos: '1루수(1B)', name: '오스틴' }, 4: { pos: '3루수(3B)', name: '문보경' }, 5: { pos: '유격수(SS)', name: '오지환' }, 6: { pos: '지명타자(DH)', name: '김현수' }, 7: { pos: '좌익수(LF)', name: '문성주' }, 8: { pos: '포수(C)', name: '박동원' }, 9: { pos: '2루수(2B)', name: '신민재' }, 'P': { pos: '투수(P)', name: '임찬규' } }
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const gameRes = await axios.get(`http://localhost:8000/api/game/${gameId}`);
        setGameInfo(gameRes.data);
        
        const [awayRes, homeRes] = await Promise.all([
          axios.get(`http://localhost:8000/api/roster?team=${gameRes.data.away_team}`),
          axios.get(`http://localhost:8000/api/roster?team=${gameRes.data.home_team}`)
        ]);
        setAwayRoster(awayRes.data);
        setHomeRoster(homeRes.data);
      } catch (e) { console.error("데이터 로딩 실패"); }
    };
    fetchData();
  }, [gameId]);

  const handleLineupChange = (teamSide, order, field, value) => {
    setLineups(prev => ({
      ...prev, [teamSide]: { ...prev[teamSide], [order]: { ...prev[teamSide][order], [field]: value } }
    }));
  };

  // 💡 백엔드로 ID와 이름을 함께 넘겨주기 위한 핵심 로직
  const handleLineupConfirm = async (side, teamName) => {
    setCrawlStatus(prev => ({ ...prev, [side]: 'crawling' }));
    
    const teamLineup = lineups[side];
    const currentRoster = side === 'away' ? awayRoster : homeRoster;

    // 로스터에서 이름으로 ID 찾기
    const getPlayerId = (name) => {
        const player = currentRoster.find(p => p.name === name);
        return player ? String(player.id) : ""; 
    };

    const pitcherName = teamLineup['P'].name;
    const pitcherId = getPlayerId(pitcherName);

    const battersInfo = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
        .map(order => {
            const bName = teamLineup[order].name;
            return { name: bName, id: getPlayerId(bName) };
        })
        .filter(b => b.name !== '');

    try {
        const response = await fetch('http://localhost:8000/api/lineup/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                team_name: teamName,
                pitcher: { name: pitcherName, id: pitcherId },
                batters: battersInfo
            }),
        });
        const data = await response.json();
        
        if (data.status === 'success') {
            setCrawlStatus(prev => ({ ...prev, [side]: 'completed' }));
            alert(`${teamName} 라인업 10명 실시간 데이터 스캔 완료!`);
        } else {
            setCrawlStatus(prev => ({ ...prev, [side]: 'error' }));
            alert(`오류 발생: ${data.message}`);
        }
    } catch (error) {
        console.error("서버 연결 에러:", error);
        setCrawlStatus(prev => ({ ...prev, [side]: 'error' }));
        alert("백엔드 서버와 연결할 수 없습니다.");
    }
  };

  if (!gameInfo) return <div style={{padding: '50px', textAlign: 'center'}}>로딩 중...</div>;

  return (
    <div style={styles.container}>
      <header style={styles.mainHeader}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>&larr; 일정</button>
        <h1 style={styles.title}>{gameInfo.away_team} vs {gameInfo.home_team} 상세 분석</h1>
        <h1 style={styles.title}> 구장 : {gameInfo.stadium} </h1>
      </header>

      <div style={styles.dualLayout}>
        {['away', 'home'].map((side) => {
          const teamName = side === 'away' ? gameInfo.away_team : gameInfo.home_team;
          const currentRoster = side === 'away' ? awayRoster : homeRoster;
          const teamTheme = teamName === '한화' ? '#ff6600' : teamName === 'LG' ? '#c0004c' : '#00a8f3';
          
          const isCrawling = crawlStatus[side] === 'crawling';
          const isCompleted = crawlStatus[side] === 'completed';

          return (
            <div key={side} style={styles.teamSection}>
              <div style={{...styles.teamHeader, borderTop: `5px solid ${teamTheme}`}}>
                <h2 style={{color: teamTheme, margin: 0}}>{teamName} 라인업</h2>
              </div>
              <table style={styles.table}>
                <thead>
                  <tr style={styles.thRow}>
                    <th style={styles.th}>타순</th>
                    <th style={styles.th}>포지션</th>
                    <th style={styles.th}>성명</th>
                  </tr>
                </thead>
                <tbody>
                  {['1', '2', '3', '4', '5', '6', '7', '8', '9', 'P'].map((order) => {
                    const availablePlayers = currentRoster.filter(p => order === 'P' ? p.position === '투수' : p.position !== '투수');
                    return (
                      <tr key={order} style={styles.tr}>
                        <td style={styles.tdNum}>{order}</td>
                        <td style={styles.td}>
                          {order === 'P' ? '투수(P)' : (
                            <select value={lineups[side][order].pos} onChange={(e) => handleLineupChange(side, order, 'pos', e.target.value)} style={styles.select}>
                              <option value="">선택</option>
                              {POSITIONS.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                          )}
                        </td>
                        <td style={styles.td}>
                          <select value={lineups[side][order].name} onChange={(e) => handleLineupChange(side, order, 'name', e.target.value)} style={styles.selectName}>
                            <option value="">선수 선택</option>
                            {lineups[side][order].name && !availablePlayers.find(p => p.name === lineups[side][order].name) && (
                                <option value={lineups[side][order].name}>{lineups[side][order].name} (테스트)</option>
                            )}
                            {availablePlayers.map(p => (
                              <option key={p.id} value={p.name}>{p.name} ({p.position[0]})</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              <div style={{ padding: '15px', textAlign: 'center', backgroundColor: '#f9f9f9' }}>
                  <button 
                      onClick={() => handleLineupConfirm(side, teamName)}
                      disabled={isCrawling || isCompleted}
                      style={{
                          width: '100%', padding: '14px', fontSize: '16px', fontWeight: 'bold', border: 'none', borderRadius: '6px', 
                          cursor: (isCrawling || isCompleted) ? 'not-allowed' : 'pointer',
                          backgroundColor: isCompleted ? '#4CAF50' : (isCrawling ? '#ccc' : teamTheme),
                          color: '#fff'
                      }}
                  >
                      {isCrawling ? "⚡ 10명 동시 실시간 스캔 중 (약 2초)..." : isCompleted ? "데이터 장전 완료 ✅" : `${teamName} 라인업 확정`}
                  </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles = {
  container: { maxWidth: '1200px', margin: '0 auto', padding: '20px' },
  mainHeader: { display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '30px' },
  backBtn: { padding: '8px 16px', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer' },
  title: { fontSize: '28px', color: '#fff', margin: 0 },
  dualLayout: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' },
  teamSection: { backgroundColor: '#fff', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.08)', overflow: 'hidden' },
  teamHeader: { padding: '20px', textAlign: 'center', backgroundColor: '#fcfcfc', borderBottom: '1px solid #eee' },
  table: { width: '100%', borderCollapse: 'collapse' },
  thRow: { backgroundColor: '#333' },
  th: { padding: '12px', color: '#fff', fontSize: '14px', textAlign: 'center' },
  tr: { borderBottom: '1px solid #eee' },
  tdNum: { padding: '12px', textAlign: 'center', fontWeight: 'bold', backgroundColor: '#f9f9f9', color: '#222' },
  td: { padding: '8px' },
  select: { width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' },
  selectName: { width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', fontWeight: 'bold' }
};

export default AnalysisPage;