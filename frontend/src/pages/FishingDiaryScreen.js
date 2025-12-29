import React, { useState, useEffect } from 'react';
import axios from 'axios';
import BottomTab from '../components/BottomTab';
import TopBar from "../components/TopBar";

// [추가] 색상 스타일 정의
const COLOR_STYLES = {
    '빨강': { bg: '#FF4D4D', text: '#FFFFFF', border: '#FF4D4D' },
    '주황': { bg: '#FF9F43', text: '#FFFFFF', border: '#FF9F43' },
    '노랑': { bg: '#FFD32A', text: '#333333', border: '#FFD32A' },
    '초록': { bg: '#2ECC71', text: '#FFFFFF', border: '#2ECC71' },
    '파랑': { bg: '#3498DB', text: '#FFFFFF', border: '#3498DB' },
    '보라': { bg: '#9B59B6', text: '#FFFFFF', border: '#9B59B6' },
    '핑크': { bg: '#EF5777', text: '#FFFFFF', border: '#EF5777' },
    '갈색': { bg: '#8D6E63', text: '#FFFFFF', border: '#8D6E63' },
    '무지개': { 
        bg: 'linear-gradient(45deg, #FF0000, #FF7F00, #FFFF00, #00FF00, #0000FF, #4B0082, #9400D3)', 
        text: '#FFFFFF', 
        border: 'transparent' 
    },
    '기타': { bg: '#95A5A6', text: '#FFFFFF', border: '#95A5A6' },
};

const FishingDiaryScreen = ({ onNavigate, user }) => {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [diaryEntries, setDiaryEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [diaryDates, setDiaryDates] = useState([]); 
  const [selectedDate, setSelectedDate] = useState(null);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [stats, setStats] = useState({ trips: 0, points: 0, cuttlefish: 0, octopus: 0 });

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
  const weekDays = ['일', '월', '화', '수', '목', '금', '토'];
  const months = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];

  useEffect(() => {
    fetchDiaries();
  }, [currentMonth]);

  const fetchDiaries = async () => { 
      setLoading(true);
      try {
        const token = localStorage.getItem('authToken');
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth() + 1;
        if (!token) { setLoading(false); return; }
        const response = await axios.get(`${API_URL}/diaries/my/`, {
          headers: { Authorization: `Token ${token}` },
          params: { year, month }
        });
        const entries = response.data;
        setDiaryEntries(entries);
        const dates = entries.map(entry => new Date(entry.fishing_date).getDate());
        setDiaryDates([...new Set(dates)]);
        
        let totalCuttle = 0; let totalOcto = 0; const pointsSet = new Set();
        entries.forEach(entry => {
           if (entry.location_name) pointsSet.add(entry.location_name);
           if (entry.catches) {
               entry.catches.forEach(c => {
                   if (c.fish_name.includes("갑오징어")) totalCuttle += c.count;
                   else if (c.fish_name.includes("쭈꾸미")) totalOcto += c.count;
               });
           }
        });
        setStats({ trips: entries.length, points: pointsSet.size, cuttlefish: totalCuttle, octopus: totalOcto });
      } catch (error) { console.error(error); } finally { setLoading(false); }
  };

  const generateCalendar = () => { 
      const year = currentMonth.getFullYear();
      const month = currentMonth.getMonth();
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);
      const daysInMonth = lastDay.getDate();
      const startingDayOfWeek = firstDay.getDay();
      const calendar = [];
      let week = new Array(7).fill(null);
      let dayCounter = 1;
      for (let i = startingDayOfWeek; i < 7 && dayCounter <= daysInMonth; i++) { week[i] = dayCounter++; }
      calendar.push([...week]);
      while (dayCounter <= daysInMonth) {
        week = new Array(7).fill(null);
        for (let i = 0; i < 7 && dayCounter <= daysInMonth; i++) { week[i] = dayCounter++; }
        calendar.push([...week]);
      }
      return calendar;
  };
  const changeMonth = (direction) => {
      const newMonth = new Date(currentMonth);
      newMonth.setMonth(currentMonth.getMonth() + direction);
      setCurrentMonth(newMonth);
      setSelectedDate(null);
  };
  const formatDayWeekday = (dateString) => {
      if (!dateString) return "";
      const date = new Date(dateString);
      return `${date.getDate()}일 ${weekDays[date.getDay()]}요일`;
  };
  const handleDelete = async (diaryId) => { 
      if (window.confirm("정말로 이 일지를 삭제하시겠습니까?")) {
        try {
          const token = localStorage.getItem('authToken');
          await axios.delete(`${API_URL}/diaries/${diaryId}/`, { headers: { Authorization: `Token ${token}` } });
          alert("삭제되었습니다."); fetchDiaries();
        } catch (err) { alert("오류 발생"); }
      }
  };

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

  const filteredEntries = selectedDate 
    ? diaryEntries.filter(entry => new Date(entry.fishing_date).getDate() === selectedDate)
    : diaryEntries;

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        <TopBar user={user} onNavigate={onNavigate} />
        
        <div className="px-5 pt-4 pb-2 bg-white sticky top-0 z-10 flex items-center justify-center">
            <h1 className="text-lg font-bold text-black">낚시 일지</h1>
        </div>

        <div className="flex-1 overflow-y-auto no-scrollbar pb-32">
          
          {/* 1. 캘린더 섹션 */}
          <div className="px-4 mt-2">
            <div className="flex justify-center items-center gap-4 mb-4 bg-gray-50 rounded-2xl py-2 mx-4">
                <button onClick={() => changeMonth(-1)} className="p-1">〈</button>
                <div className="flex gap-2 font-bold text-lg text-gray-800">
                    <span>{months[currentMonth.getMonth()]}</span>
                    <span>{currentMonth.getFullYear()}</span>
                </div>
                <button onClick={() => changeMonth(1)} className="p-1">〉</button>
            </div>
            <div className="grid grid-cols-7 gap-1 mb-2 text-center text-xs text-gray-400">
              {weekDays.map(day => <div key={day}>{day}</div>)}
            </div>
            <div className="space-y-1 mb-6">
              {generateCalendar().map((week, wIdx) => (
                <div key={wIdx} className="grid grid-cols-7 gap-1">
                  {week.map((day, dIdx) => {
                    const isSelected = day === selectedDate;
                    const hasEntry = diaryDates.includes(day);
                    const today = new Date();
                    const isToday = day === today.getDate() && currentMonth.getMonth() === today.getMonth() && currentMonth.getFullYear() === today.getFullYear();
                    return (
                      <div key={dIdx} className="flex justify-center">
                         <button
                            disabled={!day}
                            onClick={() => day && setSelectedDate(isSelected ? null : day)}
                            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${!day ? 'invisible' : ''} ${isSelected ? 'bg-blue-600 text-white shadow-md' : hasEntry ? 'bg-blue-100 text-blue-600 font-bold' : 'text-gray-700 hover:bg-gray-100'} ${isToday ? 'border-2 border-red-500' : ''}`}
                         >
                            {day}
                         </button>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          {/* 2. 이달의 요약 */}
          <div className="px-5 mb-6">
            <h2 className="font-bold text-[15px] text-gray-900 mb-3">이달의 요약</h2>
            <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm grid grid-cols-2 gap-y-3">
                <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-lg">🦑</div><div className="flex flex-col"><span className="text-xs text-gray-400">갑오징어</span><span className="text-sm font-bold text-gray-800">{stats.cuttlefish}마리</span></div></div>
                <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-lg">🚢</div><div className="flex flex-col"><span className="text-xs text-gray-400">출조</span><span className="text-sm font-bold text-gray-800">{stats.trips}회</span></div></div>
                <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-lg">🐙</div><div className="flex flex-col"><span className="text-xs text-gray-400">쭈꾸미</span><span className="text-sm font-bold text-gray-800">{stats.octopus}마리</span></div></div>
                <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-lg">📍</div><div className="flex flex-col"><span className="text-xs text-gray-400">포인트</span><span className="text-sm font-bold text-gray-800">{stats.points}곳</span></div></div>
            </div>
          </div>

          {/* 3. 상세 내용 */}
          <div className="px-5">
            <h2 className="font-bold text-[15px] text-gray-900 mb-4">상세 내용</h2>

            {loading ? (
                <div className="text-center py-10 text-gray-400">로딩 중...</div>
            ) : filteredEntries.length === 0 ? (
                <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-xl">
                    기록된 일지가 없습니다.
                </div>
            ) : (
                filteredEntries.map((entry) => (
                    <div key={entry.diary_id} className="mb-8 border-b border-gray-100 pb-6 last:border-0 relative">
                        <div className="flex justify-between items-end mb-3">
                            <span className="text-[17px] font-bold text-indigo-600">
                                {formatDayWeekday(entry.fishing_date)}
                            </span>
                            <button onClick={() => onNavigate('write', entry)} className="text-xs text-gray-400 underline hover:text-blue-600 p-1">수정</button>
                        </div>

                        {/* 상세 정보 그리드 */}
                        <div className="grid grid-cols-[50px_1fr] gap-y-2 text-[13px]">
                            <div className="font-bold text-red-500">위치</div>
                            <div className="text-gray-800 font-medium truncate">{entry.location_name || '-'} {entry.boat_name && `, ${entry.boat_name}`}</div>
                            
                            <div className="font-bold text-red-500">환경</div>
                            <div className="text-gray-800 break-keep leading-snug">
                                {formatWeather(entry.weather)}
                            </div>

                            <div className="col-span-2 flex items-start">
                                <div className="w-[50px] font-bold text-red-500 shrink-0">어종</div>
                                <div className="flex-1 text-gray-800">
                                    {entry.catches && entry.catches.length > 0 ? (
                                        <div className="flex flex-wrap gap-x-3 gap-y-1">
                                            {entry.catches.map((c, idx) => (
                                                <span key={idx} className="flex items-center">
                                                    <span className="text-gray-700">{c.fish_name}</span>
                                                    <span className="ml-1 font-bold text-emerald-500">{c.count}마리</span>
                                                    {idx < entry.catches.length - 1 && <span className="text-gray-300 ml-2">|</span>}
                                                </span>
                                            ))}
                                        </div>
                                    ) : <span className="text-gray-400">-</span>}
                                </div>
                            </div>
                            
                            {/* [수정] 에기 정보를 색상 태그로 표시 */}
                            <div className="font-bold text-red-500 mt-1">에기</div>
                            <div className="text-gray-800 flex flex-wrap gap-1 mt-1">
                                {entry.used_egis && entry.used_egis.length > 0 ? (
                                    entry.used_egis.map((e, i) => {
                                        const style = COLOR_STYLES[e.color_name] || COLOR_STYLES['기타'];
                                        return (
                                            <span 
                                                key={i} 
                                                className="text-[10px] px-2 py-0.5 rounded font-bold border"
                                                style={{
                                                    background: style.bg,
                                                    color: style.text,
                                                    borderColor: style.border === 'transparent' ? 'transparent' : style.border
                                                }}
                                            >
                                                {e.color_name}
                                            </span>
                                        );
                                    })
                                ) : (
                                    <span className="text-gray-400">정보 없음</span>
                                )}
                            </div>
                            
                            <div className="font-bold text-red-500 mt-1">메모</div>
                            <div className="text-gray-800 leading-relaxed whitespace-pre-wrap">{entry.content || "내용 없음"}</div>
                        </div>

                        <div className="mt-3">
                            <div className="text-[13px] font-bold text-red-500 mb-2">앨범</div>
                            {entry.images && entry.images.length > 0 ? (
                                <div className="flex gap-2 overflow-x-auto no-scrollbar">
                                    {entry.images.map((imgObj, idx) => {
                                        const src = imgObj.image_url?.url || imgObj.image_url || imgObj;
                                        return <img key={idx} src={src} alt="fishing" className="w-24 h-24 object-cover rounded-lg bg-gray-100 flex-shrink-0" />;
                                    })}
                                </div>
                            ) : (
                                <div className="text-xs text-gray-400 p-2 bg-gray-50 rounded">등록된 사진이 없습니다.</div>
                            )}
                        </div>

                        <div className="flex justify-end mt-2">
                            <button onClick={() => handleDelete(entry.diary_id)} className="text-[11px] font-bold text-red-500 hover:text-red-700 px-2 py-1 active:scale-95 transition-transform">🗑 삭제</button>
                        </div>
                    </div>
                ))
            )}
          </div>
        </div>

        <div className="absolute bottom-[110px] right-4 z-40">
           <button onClick={() => setShowAddMenu(!showAddMenu)} className={`w-16 h-16 rounded-full flex items-center justify-center shadow-xl transition-all ${showAddMenu ? 'bg-gray-500' : 'bg-indigo-600'}`}>
              {showAddMenu ? <span className="text-3xl text-white">✕</span> : <span className="text-3xl text-white">+</span>}
           </button>
        </div>
        {showAddMenu && (
            <div className="absolute inset-0 bg-black/50 z-30 backdrop-blur-[1px]" onClick={() => setShowAddMenu(false)}>
                <div className="absolute bottom-[190px] right-6 space-y-3 flex flex-col items-end">
                    <button onClick={() => { setShowAddMenu(false); onNavigate('voice-record'); }} className="w-14 h-14 bg-indigo-500 rounded-full flex items-center justify-center shadow-lg text-white text-2xl">🎤</button>
                    <button onClick={() => { setShowAddMenu(false); onNavigate('write'); }} className="w-14 h-14 bg-indigo-500 rounded-full flex items-center justify-center shadow-lg text-white text-2xl">📝</button>
                </div>
            </div>
        )}
        <BottomTab activeTab="diary" onNavigate={onNavigate} onCameraClick={() => setIsModalOpen(true)} />
        {isModalOpen && (
          <div className="absolute inset-0 z-[100] flex items-end justify-center px-4 pb-12 transition-all">
             <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={() => setIsModalOpen(false)}></div>
             <div className="relative w-full bg-white rounded-[32px] p-8 animate-in slide-in-from-bottom duration-300">
                <p className="text-center font-bold mb-8">입력할 방법을 선택해주세요.</p>
                <div className="flex justify-around">
                   {/* 1. 카메라 버튼 */}
                   <button 
                        onClick={() => { 
                            setIsModalOpen(false); 
                            // [수정] initialMode: 'camera' 전달
                            onNavigate('egi-recommendation', { fromPage: 'diary', initialMode: 'camera' }); 
                        }} 
                        className="..."
                    >
                      <div className="...">📷</div>
                      <span className="...">카메라</span>
                   </button>
                   {/* 2. 갤러리 버튼 */}
                   <button 
                        onClick={() => { 
                            setIsModalOpen(false); 
                            // [수정] initialMode: 'gallery' 전달
                            onNavigate('egi-recommendation', { fromPage: 'diary', initialMode: 'gallery' }); 
                        }} 
                        className="..."
                    >
                      <div className="...">🖼️</div>
                      <span className="...">갤러리</span>
                   </button>
                </div>
                <button onClick={() => setIsModalOpen(false)} className="w-full mt-8 py-4 bg-gray-50 rounded-2xl font-bold text-gray-400">취소</button>
             </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FishingDiaryScreen;