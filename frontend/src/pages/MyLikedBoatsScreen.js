import React, { useState, useEffect } from 'react';
import axios from 'axios';
import dphoImg from "../assets/dpho.jpg"; // 경로 확인 필요
import TopBar from '../components/TopBar';

// [수정] fromPage prop 추가
function MyLikedBoatsScreen({ onNavigate, fromPage, user }) {
  const [boats, setBoats] = useState([]);
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    fetchLikedBoats();
  }, []);

  const fetchLikedBoats = async () => {
    setLoading(true);
    const token = localStorage.getItem('authToken');
    
    if (!token) {
        alert("로그인이 필요합니다.");
        setLoading(false);
        return;
    }

    try {
      const response = await axios.get(`${API_URL}/boats/my-likes/`, {
        headers: { Authorization: `Token ${token}` }
      });
      if (response.data.status === 'success') {
        setBoats(response.data.results);
      }
    } catch (err) {
      console.error("찜 목록 불러오기 실패:", err);
    } finally {
      setLoading(false);
    }
  };

  // [추가] 뒤로가기 핸들러
  const handleBack = () => {
    // fromPage가 있으면 거기로, 없으면 홈으로 이동
    onNavigate(fromPage || 'home');
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        {/* [추가] 최상단 TopBar */}
        <TopBar user={user} onNavigate={onNavigate} />

        {/* 헤더 */}
        <div className="px-5 py-4 border-b border-gray-100 flex items-center relative">
            {/* [수정] onClick에 handleBack 연결 */}
            <button onClick={handleBack} className="absolute left-4 p-2 text-xl">〈</button>
            <h1 className="text-lg font-bold text-center w-full">내가 찜한 선박</h1>
        </div>

        {/* 리스트 */}
        <div className="flex-1 overflow-y-auto p-4 no-scrollbar">
             {/* ... (기존 리스트 렌더링 코드 유지) ... */}
             {loading ? (
                <div className="text-center py-20 text-gray-400">로딩 중...</div>
            ) : boats.length === 0 ? (
                <div className="text-center py-20 text-gray-400 flex flex-col items-center">
                    <span className="text-4xl mb-2">💔</span>
                    <span>아직 찜한 배가 없어요.</span>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-3">
                    {boats.map((boat) => (
                        <div 
                            key={boat.boat_id} 
                            // 상세 페이지로 갈 때도 'my-likes'에서 왔다고 알려줌
                            onClick={() => onNavigate("boat-detail", { ...boat, fromPage: 'my-likes' })}
                            className="bg-white rounded-xl p-3 border border-gray-100 shadow-sm flex gap-3 cursor-pointer active:scale-[0.98] transition-transform"
                        >
                           <div className="w-24 h-24 bg-gray-200 rounded-lg overflow-hidden shrink-0">
                                <img 
                                    src={boat.main_image_url || dphoImg} 
                                    alt={boat.name} 
                                    className="w-full h-full object-cover"
                                    onError={(e) => { e.target.onerror = null; e.target.src = dphoImg; }}
                                />
                            </div>
                            <div className="flex flex-col justify-center flex-1">
                                <span className="text-xs text-blue-500 font-bold mb-0.5">{boat.area_sea} {boat.area_main}</span>
                                <h3 className="font-bold text-gray-900 text-lg leading-tight mb-1">{boat.name}</h3>
                                <p className="text-xs text-gray-500">{boat.port} · {boat.target_fish}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>

      </div>
    </div>
  );
}

export default MyLikedBoatsScreen;