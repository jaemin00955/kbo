import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SchedulePage from './pages/SchedulePage';
import AnalysisPage from './pages/AnalysisPage'; // 상세 페이지 컴포넌트

function App() {
  return (
    <Router>
      <Routes>
        {/* 기본 주소('/')로 접속하면 '2026-04-22'로 자동 이동 */}
        <Route path="/" element={<Navigate to="/2026-04-22" replace />} />
        
        {/* 날짜를 URL 파라미터로 받는 메인 일정 페이지 */}
        <Route path="/:date" element={<SchedulePage />} />
        
        {/* 경기 상세 분석 페이지 */}
        <Route path="/analysis/:gameId" element={<AnalysisPage />} />
      </Routes>
    </Router>
  );
}


export default App;