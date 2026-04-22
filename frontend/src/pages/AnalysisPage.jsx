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
  
  // 양 팀 라인업 동시 관리
  const [lineups, setLineups] = useState({
    away: { 1: { pos: '', name: '' }, 2: { pos: '', name: '' }, 3: { pos: '', name: '' }, 4: { pos: '', name: '' }, 5: { pos: '', name: '' }, 6: { pos: '', name: '' }, 7: { pos: '', name: '' }, 8: { pos: '', name: '' }, 9: { pos: '', name: '' }, 'P': { pos: '투수(P)', name: '' } },
    home: { 1: { pos: '', name: '' }, 2: { pos: '', name: '' }, 3: { pos: '', name: '' }, 4: { pos: '', name: '' }, 5: { pos: '', name: '' }, 6: { pos: '', name: '' }, 7: { pos: '', name: '' }, 8: { pos: '', name: '' }, 9: { pos: '', name: '' }, 'P': { pos: '투수(P)', name: '' } }
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const gameRes = await axios.get(`http://localhost:8000/api/game/${gameId}`);
        setGameInfo(gameRes.data);
        
        // 원정팀, 홈팀 로스터를 동시에 불러옴
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
      ...prev,
      [teamSide]: {
        ...prev[teamSide],
        [order]: { ...prev[teamSide][order], [field]: value }
      }
    }));
  };

  if (!gameInfo) return <div style={{padding: '50px', textAlign: 'center'}}>로딩 중...</div>;

  return (
    <div style={styles.container}>
      <header style={styles.mainHeader}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>&larr; 일정</button>
        <h1 style={styles.title}>{gameInfo.away_team} vs {gameInfo.home_team} 상세 분석</h1>
        <h1 style={styles.title}> 구장 : {gameInfo.stadium} </h1>

      </header>

      {/* 듀얼 라인업 섹션 */}
      <div style={styles.dualLayout}>
        {['away', 'home'].map((side) => {
          const teamName = side === 'away' ? gameInfo.away_team : gameInfo.home_team;
          const currentRoster = side === 'away' ? awayRoster : homeRoster;
          const teamTheme = teamName === '한화' ? '#ff6600' : teamName === 'LG' ? '#c0004c' : '#00a8f3';

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
                    
                    // 💡 핵심 로직: 타순(order)에 따라 드롭다운에 보여줄 명단을 필터링합니다.
                    const availablePlayers = currentRoster.filter(p => {
                      if (order === 'P') return p.position === '투수'; // P 자리는 투수만
                      return p.position !== '투수'; // 1~9번 자리는 투수 제외 (타자만)
                    });

                    return (
                      <tr key={order} style={styles.tr}>
                        <td style={styles.tdNum}>{order}</td>
                        <td style={styles.td}>
                          {order === 'P' ? '투수' : (
                            <select 
                              value={lineups[side][order].pos}
                              onChange={(e) => handleLineupChange(side, order, 'pos', e.target.value)}
                              style={styles.select}
                            >
                              <option value="">선택</option>
                              {POSITIONS.map(p => <option key={p} value={p}>{p}</option>)}
                            </select>
                          )}
                        </td>
                        <td style={styles.td}>
                          <select 
                            value={lineups[side][order].name}
                            onChange={(e) => handleLineupChange(side, order, 'name', e.target.value)}
                            style={styles.selectName}
                          >
                            <option value="">선수 선택</option>
                            {/* 기존 currentRoster 대신 필터링된 availablePlayers를 매핑합니다 */}
                            {availablePlayers.map(p => (
                              <option key={p.id} value={p.name}>
                                {p.name} ({p.position[0]}) {/* 예: 김도영 (내) */}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
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
  title: { fontSize: '28px', color: '#ffff', margin: 0 },
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
  selectName: { width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc', fontWeight: 'bold' } // 선수명은 더 진하게
};

export default AnalysisPage;