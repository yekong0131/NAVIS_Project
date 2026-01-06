// src/pages/Home.js
import React, { useState, useEffect, useCallback } from "react";
import TopBar from "../components/TopBar";
import axios from "axios";
import pandaBanner from "../assets/1.gif"; 
import dphoImg from "../assets/dpho.jpg"; 
import BottomTab from '../components/BottomTab';
import defaultEgiImg from "../assets/ndchjegi.jpg";

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const getUserLocation = () => {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation을 지원하지 않는 브라우저입니다.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ lat: position.coords.latitude, lon: position.coords.longitude }),
      (error) => reject(new Error('위치 정보를 가져올 수 없습니다.')),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  });
};

function Home({ onNavigate, user, environmentData, setEnvironmentData }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [recommendedEgis, setRecommendedEgis] = useState([]);
  const [likedBoats, setLikedBoats] = useState([]);
  

  const [loadingEnv, setLoadingEnv] = useState(false);

  // === 환경 정보 로직 ===
  const fetchEnvironmentData = useCallback(async (forceRefresh = false) => {
    if (!forceRefresh && environmentData) return;

    setLoadingEnv(true);
    try {
      const location = await getUserLocation();
      const envRes = await axios.get(`${API_URL}/ocean/`, {
        params: { lat: location.lat, lon: location.lon, target_fish: '쭈갑' }
      });
      const data = envRes.data;
      
      // 부모(App)의 상태 업데이트 -> 데이터 영구 저장
      setEnvironmentData({
        tide: data.moon_phase ? `${data.moon_phase}물` : '정보 없음',
        wind_speed: data.wind_speed ? `${data.wind_speed} m/s` : '정보 없음',
        wind_direction: data.wind_direction_16 || '정보 없음',
        water_temp: data.water_temp ? `${data.water_temp}°C` : '정보 없음',
        weather: data.rain_type_text || '정보 없음',
        current_strength: data.current_speed ? 
          (data.current_speed < 0.3 ? '약함' : data.current_speed < 0.7 ? '중간' : '강함') : '정보 없음',
        location_name: data.location_name || '현재 위치',
        fishing_index: data.fishing_index || '',
        high_tide: data.next_high_tide || '-', 
        low_tide: data.next_low_tide || '-',
      });
    } catch (err) {
      console.error('환경 정보 로딩 실패:', err);
      // 실패 시에도 부모 상태 업데이트 (더미 데이터 등)
      if (!environmentData) { 
          setEnvironmentData({
            tide: "8물", wind_speed: "3.2 m/s", wind_direction: "북동", water_temp: "18.5°C",
            weather: "맑음", current_strength: "중간", location_name: "위치 정보 없음"
          });
      }
    } finally {
      setLoadingEnv(false);
    }
  }, [environmentData, setEnvironmentData]); // 의존성 추가

  useEffect(() => {
    const fetchData = async () => {
        const token = localStorage.getItem('authToken');
        if (user && token) {
            try {
                const boatRes = await axios.get(`${API_URL}/boats/my-likes/`, {
                    headers: { Authorization: `Token ${token}` }
                });
                if (boatRes.data.status === 'success') setLikedBoats(boatRes.data.results);
            } catch (err) {}
        }
        try {
            const egiRes = await axios.get(`${API_URL}/egis/`);
            setRecommendedEgis(egiRes.data);
        } catch (err) {}
        
        // 데이터가 없을 때만 초기 수집 실행
        if (!environmentData) {
            fetchEnvironmentData(false);
        }
    };
    fetchData();
  }, [user, environmentData, fetchEnvironmentData]);

  const getWeatherIcon = (weather) => {
    if (!weather) return '🌤️';
    if (weather.includes('맑음')) return '☀️';
    if (weather.includes('흐림')) return '☁️';
    if (weather.includes('비')) return '🌧️';
    return '🌤️';
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        
        <TopBar user={user} onNavigate={onNavigate} />

        <div className={`flex-1 overflow-y-auto no-scrollbar transition-all duration-300 ${isModalOpen ? 'brightness-50' : ''}`} style={{ paddingBottom: '200px' }}>
          
          {/* 배너 */}
          <div className="px-5 mt-4">
            <div className="relative w-full h-[170px] rounded-[28px] overflow-hidden shadow-sm">
              <img src={pandaBanner} alt="Banner" className="w-full h-full object-cover" />
            </div>
          </div>

          {/* 환경 정보 카드 */}
          <div className="px-5 mt-6 relative z-30 text-black"> 
             <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-[17px] text-black font-sans">
                현재 낚시 환경 🌊
              </h3>
              {/* 새로고침 버튼: forceRefresh=true 전달하여 강제 업데이트 */}
              <button
                onClick={() => fetchEnvironmentData(true)}
                disabled={loadingEnv}
                className="text-xs text-blue-500 font-medium active:opacity-70 disabled:opacity-40"
              >
                {loadingEnv ? '새로고침 중...' : '🔄 새로고침'}
              </button>
            </div>

            {environmentData && (
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-[20px] p-4 shadow-sm border border-blue-100">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b border-blue-200">
                  <span className="text-xs text-gray-500">📍</span>
                  <span className="text-xs text-gray-700 font-medium">
                    {environmentData.location_name}
                  </span>
                  {environmentData.fishing_index && (
                    <span className={`text-xs px-2 py-0.5 rounded-full font-bold ml-auto ${
                      environmentData.fishing_index.includes('좋음') ? 'bg-green-100 text-green-700' :
                      environmentData.fishing_index.includes('보통') ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {environmentData.fishing_index}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                    <div className="text-xl mb-1">🌊</div>
                    <p className="text-[10px] text-gray-500 font-medium mb-1">물때</p>
                    <p className="text-[13px] font-bold text-gray-800">{environmentData.tide}</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                    <div className="text-xl mb-1">💨</div>
                    <p className="text-[10px] text-gray-500 font-medium mb-1">풍속</p>
                    <p className="text-[13px] font-bold text-gray-800">{environmentData.wind_speed}</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                    <div className="text-xl mb-1">🧭</div>
                    <p className="text-[10px] text-gray-500 font-medium mb-1">풍향</p>
                    <p className="text-[13px] font-bold text-gray-800">{environmentData.wind_direction}</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                    <div className="text-xl mb-1">🌡️</div>
                    <p className="text-[10px] text-gray-500 font-medium mb-1">수온</p>
                    <p className="text-[13px] font-bold text-gray-800">{environmentData.water_temp}</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                    <div className="text-xl mb-1">{getWeatherIcon(environmentData.weather)}</div>
                    <p className="text-[10px] text-gray-500 font-medium mb-1">날씨</p>
                    <p className="text-[13px] font-bold text-gray-800">{environmentData.weather}</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                    <div className="text-xl mb-1">🌀</div>
                    <p className="text-[10px] text-gray-500 font-medium mb-1">조류</p>
                    <p className="text-[13px] font-bold text-gray-800">{environmentData.current_strength}</p>
                  </div>
                </div>
                <div className="bg-white rounded-xl py-3 px-4 shadow-sm flex items-center justify-around border border-blue-50">
                  {/* 만조 */}
                  <div className="flex flex-col items-center w-1/2"> {/* w-1/2로 영역 확보 */}
                      <span className="text-[10px] text-gray-500 mb-1">다음 만조</span>
                      <div className="relative flex items-center justify-center">
                          <span className="absolute right-full mr-1.5 text-red-500 text-[10px] font-bold top-1/2 -translate-y-1/2">
                              ▲
                          </span>
                          <span className="text-[15px] font-extrabold text-gray-700 tracking-tight leading-none">
                              {environmentData.high_tide}
                          </span>
                      </div>
                  </div>
                  <div className="w-[1px] h-8 bg-gray-100"></div>
                  {/* 간조 */}
                  <div className="flex flex-col items-center w-1/2">
                      <span className="text-[10px] text-gray-500 mb-1">다음 간조</span>
                      <div className="relative flex items-center justify-center">
                          <span className="absolute right-full mr-1.5 text-blue-500 text-[10px] font-bold top-1/2 -translate-y-1/2">
                              ▼
                          </span>
                          <span className="text-[15px] font-extrabold text-gray-700 tracking-tight leading-none">
                              {environmentData.low_tide}
                          </span>
                      </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 선박 리스트 */}
          <div className="px-5 mt-8">
            <div 
                className="flex justify-between items-center mb-4 cursor-pointer active:opacity-70 transition-opacity"
                onClick={() => onNavigate('my-likes', { fromPage: 'home' })}
            >
                <h3 className="font-bold text-[17px] text-black font-sans">
                    내가 찜한 선박 <span className="text-gray-400 ml-1 text-sm">({likedBoats.length})</span>
                </h3>
                <span className="text-gray-400 font-bold text-lg">〉</span>
            </div>
            {likedBoats.length > 0 ? (
                <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
                    {likedBoats.slice(0, 5).map((boat) => (
                       <div key={boat.boat_id} className="min-w-[140px]" onClick={() => onNavigate('boat-detail', { ...boat, fromPage: 'home' })}>
                            <div className="w-[140px] h-[140px] bg-gray-100 rounded-[24px] overflow-hidden border border-gray-50 shadow-sm">
                                <img src={boat.main_image_url || dphoImg} alt={boat.name} className="w-full h-full object-cover" onError={(e) => { e.target.src = dphoImg; }} />
                            </div>
                            <p className="text-[13px] font-bold mt-2 text-center text-gray-800 truncate px-1">{boat.name}</p>
                        </div>
                    ))}
                </div>
            ) : (
                <div className="bg-gray-50 rounded-2xl p-6 text-center" onClick={() => onNavigate('boat-search')}>
                    <p className="text-xs text-gray-500 font-bold mb-1">아직 찜한 선박이 없어요.</p>
                </div>
            )}
          </div>

          {/* 에기 리스트 */}
          <div className="px-5 mt-8">
            <div 
                className="flex justify-between items-center mb-4 cursor-pointer active:opacity-70 transition-opacity"
                onClick={() => onNavigate('egi-list', { fromPage: 'home' })}
            >
                <h3 className="font-bold text-[17px] text-black font-sans">이런 에기는 어떠세요?</h3>
                <span className="text-gray-400 font-bold text-lg">〉</span>
            </div>

            {recommendedEgis.length > 0 ? (
                <div className="flex gap-4 overflow-x-auto no-scrollbar pb-6">
                {recommendedEgis.map((egi) => (
                    <div key={egi.egi_id} className="min-w-[140px]" onClick={() => onNavigate('egi-detail', { ...egi, fromPage: 'home' })}>
                        <div className="w-[140px] h-[140px] bg-white rounded-[24px] overflow-hidden border border-gray-100 shadow-sm relative">
                            <img 
                                src={egi.image_url || defaultEgiImg} 
                                alt={egi.name} 
                                className="w-full h-full object-contain p-2" 
                                onError={(e) => { e.target.src = defaultEgiImg; }} 
                            />
                        </div>
                        <p className="text-[13px] font-bold mt-2 text-center text-gray-800 px-1 line-clamp-3 leading-tight h-[50px] flex items-start justify-center">
                            {egi.name}
                        </p>
                    </div>
                ))}
                </div>
            ) : (
                <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-2xl"><p className="text-xs">등록된 추천 에기가 없습니다.</p></div>
            )}
          </div>
        </div>

        <BottomTab activeTab="home" onNavigate={onNavigate} onCameraClick={() => setIsModalOpen(true)} />

        {/* 카메라 모달 */}
        {isModalOpen && (
          <div className="absolute inset-0 z-[100] flex items-end justify-center px-4 pb-12 transition-all">
            <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={() => setIsModalOpen(false)}></div>
            <div className="relative w-full bg-white rounded-[32px] overflow-hidden shadow-2xl p-8 animate-in slide-in-from-bottom duration-300">
              <p className="text-center text-gray-800 font-bold mb-8 text-[15px]">입력할 방법을 선택해주세요.</p>
              <div className="flex justify-around items-center">
                
                {/* 1. 카메라 버튼 */}
                <button 
                    onClick={() => { 
                        setIsModalOpen(false); 
                        onNavigate('egi-recommendation', { fromPage: 'home', initialMode: 'camera' }); 
                    }} 
                    className="flex flex-col items-center gap-3"
                >
                  <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center text-3xl shadow-sm border border-gray-100">📷</div>
                  <span className="text-xs font-bold text-gray-600">카메라</span>
                </button>

                {/* 2. 갤러리 버튼 */}
                <button 
                    onClick={() => { 
                        setIsModalOpen(false); 
                        onNavigate('egi-recommendation', { fromPage: 'home', initialMode: 'gallery' }); 
                    }} 
                    className="flex flex-col items-center gap-3"
                >
                  <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center text-3xl shadow-sm border border-gray-100">🖼️</div>
                  <span className="text-[13px] font-bold text-gray-600">갤러리</span>
                </button>

              </div>
              <button onClick={() => setIsModalOpen(false)} className="w-full mt-8 py-4 bg-gray-50 rounded-2xl text-gray-400 font-bold active:bg-gray-100 transition-colors">취소</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;