import React, { useState, useEffect } from 'react';
import axios from 'axios';
import dphoImg from "../assets/dpho.jpg"; 
import TopBar from '../components/TopBar';

const WebViewModal = ({ url, onClose }) => {
  if (!url) return null;
  return (
    <div className="absolute inset-0 z-50 flex flex-col bg-white animate-in slide-in-from-bottom duration-300">
      <div className="flex justify-between items-center px-4 py-3 border-b border-gray-200 bg-white shadow-sm shrink-0">
        <span className="font-bold text-gray-800 text-sm truncate flex-1 pr-4">{url}</span>
        <button onClick={onClose} className="px-3 py-1 bg-gray-100 text-gray-600 rounded-lg text-sm font-bold active:bg-gray-200 shrink-0">닫기 ✕</button>
      </div>
      <div className="flex-1 w-full h-full bg-gray-50 relative">
        <iframe src={url} title="Booking WebView" className="w-full h-full border-0" />
      </div>
    </div>
  );
};

function BoatDetailScreen({ boat, onNavigate, user }) {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [webViewUrl, setWebViewUrl] = useState(null);
  const [isLiked, setIsLiked] = useState(false);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  // [핵심 로직] 어디서 왔는지(fromPage)에 따라 뒤로가기 경로 결정
  const handleBack = () => {
    if (boat && boat.fromPage) {
        onNavigate(boat.fromPage); // 'home', 'my-likes', 'boat-search' 중 하나로 이동
    } else {
        onNavigate('boat-search'); // 정보가 없으면 기본값인 '조회' 페이지로
    }
  };
  
  useEffect(() => {
    if (boat?.boat_id) {
        fetchSchedules();
        setIsLiked(boat.is_liked || false);
    }
  }, [boat]);

  const fetchSchedules = async () => {
    setLoading(true);
    try {
        const response = await axios.get(`${API_URL}/boats/${boat.boat_id}/schedules/`, {
            params: { days: 14 } 
        });
        
        if (response.data.status === 'success') {
            setSchedules(response.data.schedules);
        }
    } catch (err) {
        console.error("스케줄 로딩 실패:", err);
    } finally {
        setLoading(false);
    }
  };

  if (!boat) return null;

  const handleToggleLike = async () => {
    const token = localStorage.getItem('authToken');
    if (!token) { alert("로그인이 필요합니다."); return; }
    const originalState = isLiked;
    setIsLiked(!isLiked);
    try {
        await axios.post(`${API_URL}/boats/like/${boat.boat_id}/`, {}, { headers: { Authorization: `Token ${token}` } });
    } catch (error) {
        setIsLiked(originalState);
    }
  };

  const handleBookingClick = () => {
    if (!boat.booking_url) { alert("예약 URL 정보가 없습니다."); return; }
    setWebViewUrl(boat.booking_url); 
  };

  const handleScheduleClick = (sch) => {
    if (sch.available_count <= 0) {
        alert("마감된 일정입니다.");
        return;
    }
    const shipNo = boat.ship_no || 0; 
    const dateValue = sch.date || sch.sdate || ""; 
    const targetUrl = `https://www.sunsang24.com/ship/list/?ship_no=${shipNo}&sdate=${dateValue}`;
    setWebViewUrl(targetUrl);
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        {/* 상단 네비게이션 */}
        <div className="absolute top-0 left-0 right-0 px-4 pt-8 flex justify-between items-center z-10">
          {/* [수정됨] onClick에 handleBack 함수 연결 */}
          <button 
            onClick={handleBack} 
            className="w-9 h-9 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-sm text-lg"
          >
            〈
          </button>
          
          <button onClick={handleToggleLike} className={`w-9 h-9 backdrop-blur-sm rounded-full flex items-center justify-center shadow-sm transition-all active:scale-90 ${isLiked ? "bg-red-50 text-red-500 border border-red-100" : "bg-white/90 text-gray-300"}`}>{isLiked ? "♥" : "♡"}</button>
        </div>

        {/* 메인 이미지 */}
        <div className="w-full h-[260px] bg-gray-200 shrink-0 relative">
          <img src={boat.main_image_url || dphoImg} alt={boat.name} className="w-full h-full object-cover" onError={(e) => { e.target.onerror = null; e.target.src = dphoImg; }} />
        </div>

        {/* 콘텐츠 영역 */}
        <div className="flex-1 overflow-y-auto -mt-6 bg-white rounded-t-[32px] relative z-0 pb-24 no-scrollbar">
          <div className="px-5 pt-8 pb-5 border-b border-gray-50">
            <div className="flex gap-1.5 mb-2">
              <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 text-[11px] font-bold rounded">{boat.area_sea}</span>
              <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-[11px] font-bold rounded">{boat.area_main}</span>
            </div>
            <h1 className="text-xl font-bold text-gray-900 mb-1">{boat.name}</h1>
            <p className="text-gray-500 text-[13px] flex items-center gap-1">📍 {boat.address}</p>
          </div>

          <div className="px-5 py-5 border-b border-gray-50">
            <h3 className="font-bold text-[15px] mb-2 text-gray-900">선박 소개</h3>
            {boat.intro_memo ? (
                <div className="text-gray-600 text-[13px] leading-relaxed whitespace-pre-line" dangerouslySetInnerHTML={{ __html: boat.intro_memo }} />
            ) : (<p className="text-gray-400 text-[13px]">소개글이 없습니다.</p>)}
          </div>

          <div className="px-5 py-5">
            <h3 className="font-bold text-[15px] mb-3 text-gray-900">예약 일정</h3>
            {loading && <div className="text-center py-4 text-gray-400 text-xs">일정을 불러오는 중...</div>}
            
            <div className="space-y-2.5">
              {schedules.map((sch, idx) => {
                const dateStr = sch.date || sch.sdate || "";
                const formattedDate = dateStr.length >= 5 ? dateStr.substring(5).replace('-', '.') : dateStr;

                return (
                  <div 
                      key={idx} 
                      onClick={() => handleScheduleClick(sch)} 
                      className="flex items-center justify-between p-3.5 rounded-xl border border-gray-100 bg-gray-50/50 active:bg-gray-100 transition-colors cursor-pointer"
                  >
                    <div className="flex flex-col">
                      <span className="font-bold text-[14px] text-gray-800">
                        {formattedDate} 
                        <span className={`text-xs ml-1 ${sch.day_of_week === '일' ? 'text-red-500' : sch.day_of_week === '토' ? 'text-blue-500' : 'text-gray-500'}`}>({sch.day_of_week})</span>
                      </span>
                      <span className="text-[11px] text-blue-500 font-bold mt-0.5">Target: {sch.fish_type || boat.target_fish}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-[14px] text-gray-900">{Number(sch.price).toLocaleString()}원</div>
                      {sch.available_count > 0 ? (
                        <span className="text-[11px] font-bold text-red-500">
                          잔여 {sch.available_count} / {sch.total_count}석
                        </span>
                      ) : (
                        <span className="text-[11px] font-bold text-gray-400">마감</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 하단 고정 버튼 */}
        <div className="absolute bottom-0 left-0 w-full bg-white border-t border-gray-100 px-5 py-3 pb-6 flex gap-3 z-20">
          <a href={`tel:${boat.contact || boat.phone}`} className="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center text-xl shadow-md active:scale-95 transition-transform">📞</a>
          <button className="flex-1 bg-gray-900 text-white rounded-xl font-bold text-[15px] shadow-md active:scale-[0.98] transition-transform" onClick={handleBookingClick}>예약하기</button>
        </div>

        {webViewUrl && (<WebViewModal url={webViewUrl} onClose={() => setWebViewUrl(null)} />)}
      </div>
    </div>
  );
}

export default BoatDetailScreen;