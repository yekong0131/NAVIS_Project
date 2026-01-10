import React, { useState, useEffect, useMemo } from "react";
import axios from "axios";
import dphoImg from "../assets/dpho.jpg"; // 기본 이미지
import TopBar from '../components/TopBar';

function DiarySummary({ onBack, user, onNavigate }) {
  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(true);
  
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({
    thisYear: { trips: 0, total_catch: 0, jjukkumi: 0, cuttlefish: 0, top_location: '-' },
    diff: { trip: 0, catch: 0 }
  });

  const currentYear = new Date().getFullYear();
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    const fetchSummary = async () => {
      const token = localStorage.getItem('authToken');
      if (!token) return;

      try {
        setLoading(true);
        // year 파라미터는 '통계' 계산용으로 사용되고, logs는 전체가 반환됨
        const response = await axios.get(`${API_URL}/diaries/summary/`, {
          headers: { Authorization: `Token ${token}` },
          params: { year: currentYear }
        });

        const data = response.data;
        setLogs(data.logs); // 전체 일지 목록
        setStats({
          thisYear: data.this_year,
          lastYear: data.last_year,
          diff: data.diff
        });

      } catch (err) {
        console.error("일지 요약 로딩 실패:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [currentYear]);

  // 앨범용 이미지 추출 (전체 일지 기준)
  const albumImages = useMemo(() => {
    if (!logs) return [];
    return logs.flatMap(log => log.images || []); 
  }, [logs]);

  // 이미지 주소 처리 헬퍼 함수
  const getImageUrl = (imgObj) => {
    if (!imgObj) return dphoImg;
    if (imgObj.image_url) return imgObj.image_url;
    if (typeof imgObj === 'string') return imgObj;
    return dphoImg;
  };

  // 날짜 포맷팅 함수 (YYYY-MM-DD)
  const formatDate = (dateString) => {
    if (!dateString) return "";
    return dateString.split("T")[0];
  };

  // [추가] 환경 정보 포맷팅 함수 (FishingDiaryScreen과 동일)
  const formatWeather = (weather) => {
    if (!weather) return '-';
    
    const parts = [];
    if (weather.moon_phase) parts.push(`${weather.moon_phase}물`);
    if (weather.temperature) parts.push(`기온 ${weather.temperature}℃`);
    if (weather.water_temp) parts.push(`수온 ${weather.water_temp}℃`);
    if (weather.current_speed) parts.push(`조류 ${weather.current_speed}m/s`);
    if (weather.wind_speed) parts.push(`풍속 ${weather.wind_speed}m/s(${weather.wind_direction_16 || '-'})`);
    if (weather.weather_status) parts.push(`${weather.weather_status}`);

    return parts.length > 0 ? parts.join(' · ') : '-';
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
      {/* [추가] 최상단 TopBar */}
      <TopBar user={user} onNavigate={onNavigate} />

        {/* 상단 네비게이션 */}
        <div className="px-5 pt-8 pb-2 bg-white flex flex-col z-10 border-b border-gray-50 flex-shrink-0">
          <div className="relative flex items-center justify-center mb-4">
            {/* 뒤로가기 버튼 */}
            <button 
              onClick={onBack} 
              className="absolute left-0 w-8 h-8 flex items-center justify-center text-xl text-gray-600 active:bg-gray-100 rounded-full transition-colors"
            >
              〈
            </button>
            
            {/* 탭 버튼들 */}
            <div className="flex gap-6 text-[14px] font-bold text-gray-400">
              <span onClick={() => setActiveTab('all')} className={`cursor-pointer transition-colors ${activeTab === 'all' ? 'text-black border-b-2 border-black pb-1' : 'hover:text-gray-600'}`}>전체</span>
              <span onClick={() => setActiveTab('album')} className={`cursor-pointer transition-colors ${activeTab === 'album' ? 'text-black border-b-2 border-black pb-1' : 'hover:text-gray-600'}`}>앨범</span>
              <span onClick={() => setActiveTab('summary')} className={`cursor-pointer transition-colors ${activeTab === 'summary' ? 'text-black border-b-2 border-black pb-1' : 'hover:text-gray-600'}`}>요약</span>
            </div>
            
            <div className="absolute right-0 w-8 h-8"></div>
          </div>
          
          <h2 className="text-[22px] font-bold text-left mt-2">
            {activeTab === 'summary' ? `${currentYear}년 결산` : `나의 낚시 기록`}
          </h2>
        </div>

        {/* 컨텐츠 영역 */}
        <div className="flex-1 overflow-y-auto no-scrollbar bg-gray-50">
          {loading ? (
             <div className="flex h-full items-center justify-center text-gray-400 text-sm">로딩 중...</div>
          ) : (
            <>
              {/* [탭 1] 전체 리스트 */}
              {activeTab === 'all' && (
                <div className="px-5 py-4 pb-24 bg-white min-h-full">
                  {logs.length === 0 ? (
                      <div className="text-center py-20 text-gray-400 text-sm">작성된 일지가 없습니다.</div>
                  ) : logs.map((log) => (
                    <div key={log.diary_id} className="mb-8">
                      {/* 날짜 표시 */}
                      <h3 className="text-[16px] font-bold text-blue-600 mb-3 text-left">
                        {formatDate(log.fishing_date)}
                      </h3>
                      <div className="text-[13px] space-y-1.5 text-left mb-3 pl-1">
                        <div className="flex gap-2"><span className="font-bold text-red-500 w-10 shrink-0">위치</span><span className="text-gray-700">{log.location_name || "-"}</span></div>
                        
                        {/* [수정] 환경 정보 상세 출력 */}
                        <div className="flex gap-2">
                            <span className="font-bold text-red-500 w-10 shrink-0">환경</span>
                            <span className="text-gray-700 break-keep leading-snug">
                                {formatWeather(log.weather)}
                            </span>
                        </div>

                        <div className="flex gap-2"><span className="font-bold text-red-500 w-10 shrink-0">조과</span><span className="text-gray-900 font-bold">{log.species}</span></div>
                        <div className="flex gap-2 mt-2"><span className="font-bold text-red-500 w-10 shrink-0">메모</span><span className="text-gray-600 leading-snug line-clamp-2">{log.content}</span></div>
                      </div>
                      
                      {/* 앨범 스크롤 */}
                      {log.images && log.images.length > 0 && (
                        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-2">
                          {log.images.map((imgObj, idx) => {
                            const src = getImageUrl(imgObj);
                            return (
                              <div key={idx} className="w-28 h-28 flex-shrink-0 rounded-xl overflow-hidden border border-gray-100 bg-gray-50">
                                <img 
                                  src={src} 
                                  alt="catch" 
                                  className="w-full h-full object-cover"
                                  onError={(e) => { e.target.onerror = null; e.target.src = dphoImg; }}
                                />
                              </div>
                            );
                          })}
                        </div>
                      )}
                      <div className="h-[1px] bg-gray-100 w-full mt-6"></div>
                    </div>
                  ))}
                </div>
              )}

              {/* [탭 2] 앨범 (전체 사진) */}
              {activeTab === 'album' && (
                <div className="p-1 pb-24 min-h-full bg-white">
                  {albumImages.length > 0 ? (
                    <div className="grid grid-cols-3 gap-1">
                      {albumImages.map((imgObj, idx) => {
                        const src = getImageUrl(imgObj);
                        return (
                          <div key={idx} className="aspect-square bg-gray-100 overflow-hidden cursor-pointer">
                            <img 
                              src={src} 
                              alt={`album-${idx}`} 
                              className="w-full h-full object-cover hover:scale-110 transition-transform duration-300"
                              onError={(e) => { e.target.onerror = null; e.target.src = dphoImg; }}
                            />
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-20 text-gray-400 text-sm">등록된 사진이 없습니다.</div>
                  )}
                </div>
              )}

              {/* [탭 3] 요약 (통계 - 올해 기준) */}
              {activeTab === 'summary' && (
                <div className="px-5 py-6 pb-24 space-y-6">
                  {/* 통계 카드들 (기존 유지) */}
                  <div className="bg-white rounded-[24px] p-6 shadow-sm border border-gray-100">
                    <h3 className="font-bold text-lg mb-4 text-gray-800">🎣 올해의 조과</h3>
                    <div className="flex justify-around items-center text-center">
                      <div className="flex flex-col">
                        <span className="text-3xl font-black text-blue-600">{stats.thisYear.jjukkumi}</span>
                        <span className="text-xs text-gray-500 font-bold mt-1">쭈꾸미 (마리)</span>
                      </div>
                      <div className="w-[1px] h-10 bg-gray-200"></div>
                      <div className="flex flex-col">
                        <span className="text-3xl font-black text-purple-600">{stats.thisYear.cuttlefish}</span>
                        <span className="text-xs text-gray-500 font-bold mt-1">갑오징어 (마리)</span>
                      </div>
                    </div>
                    <div className="mt-6 pt-4 border-t border-dashed border-gray-200 text-center">
                      <p className="text-sm text-gray-600">올해 총 <span className="font-bold text-black">{stats.thisYear.total_catch}마리</span>를 잡으셨네요! 🎉</p>
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-[24px] p-6 shadow-lg text-white">
                    <h3 className="font-bold text-lg mb-1 opacity-90">작년과 비교하면?</h3>
                    <p className="text-xs opacity-70 mb-6">{currentYear - 1}년 데이터와 비교한 수치입니다.</p>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold opacity-90">출조 횟수</span>
                        <div className="flex items-center gap-2">
                            <span className="text-2xl font-black">{stats.thisYear.trips}회</span>
                            <span className={`text-xs font-bold px-2 py-1 rounded-full ${stats.diff.trip >= 0 ? 'bg-white/20 text-white' : 'bg-red-500/20 text-white'}`}>{stats.diff.trip >= 0 ? `+${stats.diff.trip}회` : `${stats.diff.trip}회`}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold opacity-90">총 조과</span>
                        <div className="flex items-center gap-2">
                            <span className="text-2xl font-black">{stats.thisYear.total_catch}마리</span>
                            <span className={`text-xs font-bold px-2 py-1 rounded-full ${stats.diff.catch >= 0 ? 'bg-white/20 text-white' : 'bg-red-500/20 text-white'}`}>{stats.diff.catch >= 0 ? `+${stats.diff.catch}마리` : `${stats.diff.catch}마리`}</span>
                        </div>
                      </div>
                    </div>
                    <div className="mt-6 pt-4 border-t border-white/20 text-center">
                      <p className="text-[15px] font-bold leading-relaxed">"작년보다 <span className="text-yellow-300">{Math.abs(stats.diff.trip)}번</span> {stats.diff.trip >= 0 ? '더' : '덜'} 출조하고,<br/> <span className="text-yellow-300">{Math.abs(stats.diff.catch)}마리</span> {stats.diff.catch >= 0 ? '더' : '덜'} 잡으셨네요!"</p>
                    </div>
                  </div>

                  <div className="bg-white rounded-[24px] p-6 shadow-sm border border-gray-100 flex items-center justify-between">
                     <div><h3 className="font-bold text-gray-800 text-sm mb-1">가장 많이 찾은 바다</h3><p className="text-2xl font-black text-gray-900">{stats.thisYear.top_location}</p></div>
                     <div className="text-4xl">🗺️</div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default DiarySummary;