import React, { useState, useRef, useEffect } from "react";
import TopBar from "../components/TopBar";
import axios from "axios";
import pandaBanner from "../assets/panda_banner.png"; 
import dphoImg from "../assets/dpho.jpg"; 
import BottomTab from '../components/BottomTab';
import defaultEgiImg from "../assets/ndchjegi.jpg";

// [결과 화면용 이미지]
import wangpandaImg from "../assets/login_panda.png"; 
import oliveImg from "../assets/hgegi.jpg"; 
import nbgImg from "../assets/ndchjegi.jpg"; 
import wdhlImg from "../assets/dpho.jpg"; 

function Home({ onCapture, onNavigate, user }) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState("home"); 
  const [capturedImage, setCapturedImage] = useState(null);
  
  const [recommendedEgis, setRecommendedEgis] = useState([]);
  const [likedBoats, setLikedBoats] = useState([]);
  
  // [환경 정보 상태]
  const [environmentData, setEnvironmentData] = useState(null);
  const [loadingEnv, setLoadingEnv] = useState(false);
  const [locationError, setLocationError] = useState(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);

  // [결과 화면용] 추천 에기 데이터
  const resultRecEgis = [
    { id: 1, name: "EGI-OH K 네온 브라이트 그린", desc: "탁한 물에서도 뚫고 나오는 강력한 존재감", img: nbgImg },
    { id: 2, name: "EGI-OH K #077 올리브 애시", desc: "내추럴한 올리브 컬러와 녹색 광의 조화", img: oliveImg },
    { id: 3, name: "EGI-OH K #076 와일드 하울", desc: "저조도 상황을 압도하는 플래시 효과", img: wdhlImg },
  ];

  // === 환경 정보 로직 ===
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

  const fetchEnvironmentData = async () => {
    setLoadingEnv(true);
    setLocationError(null);
    try {
      const location = await getUserLocation();
      const envRes = await axios.get(`${API_URL}/ocean/`, {
        params: { lat: location.lat, lon: location.lon, target_fish: '쭈갑' }
      });
      const data = envRes.data;
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
        wave_height: data.wave_height ? `${data.wave_height}m` : '0.5m',
      });
    } catch (err) {
      console.error('환경 정보 로딩 실패:', err);
      setLocationError("위치 정보를 불러올 수 없습니다.");
      setEnvironmentData({
        tide: "8물", wind_speed: "3.2 m/s", wind_direction: "북동", water_temp: "18.5°C",
        weather: "맑음", current_strength: "중간", location_name: "위치 정보 없음"
      });
    } finally {
      setLoadingEnv(false);
    }
  };

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
        fetchEnvironmentData();
    };
    fetchData();
  }, [user]);

  // === 카메라 로직 ===
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch (err) {
      alert("카메라 권한이 필요합니다.");
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  useEffect(() => {
    if (viewMode === "camera") {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
  }, [viewMode]);

  const takePhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (video && canvas) {
      const context = canvas.getContext("2d");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = canvas.toDataURL("image/png");
      setCapturedImage(imageData);
      processCapture(); 
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setCapturedImage(reader.result);
        setIsModalOpen(false);
        processCapture();
      };
      reader.readAsDataURL(file);
    }
  };

  const processCapture = () => {
    stopCamera();
    setViewMode("result");
    if (onCapture) onCapture(true);
  };

  const getWeatherIcon = (weather) => {
    if (!weather) return '🌤️';
    if (weather.includes('맑음')) return '☀️';
    if (weather.includes('흐림')) return '☁️';
    if (weather.includes('비')) return '🌧️';
    return '🌤️';
  };

  // ============================================================
  // 3. 화면 렌더링
  // ============================================================

  // [A] 카메라 화면
  if (viewMode === "camera") {
    return (
      <div className="fixed inset-0 bg-slate-900 flex justify-center items-center z-[100]">
        <div className="relative w-full max-w-[420px] h-full bg-black flex flex-col">
          <div className="px-6 pt-12 flex justify-between items-center z-10 text-white">
            <button onClick={() => { setViewMode("home"); stopCamera(); }} className="text-2xl font-bold text-white">✕</button>
            <span className="text-sm font-medium tracking-widest uppercase font-bold text-gray-400">Live View</span>
            <div className="w-6 h-6"></div>
          </div>
          <div className="flex-1 relative flex items-center justify-center bg-gray-900 overflow-hidden">
             <video ref={videoRef} autoPlay playsInline className="absolute inset-0 w-full h-full object-cover" />
             <canvas ref={canvasRef} className="hidden" />
          </div>
          <div className="h-44 bg-black flex items-center justify-between px-10 pb-10 relative text-white">
            <div className="w-14 h-14 rounded-xl bg-gray-800 overflow-hidden border border-white/10 flex items-center justify-center">
              {capturedImage ? <img src={capturedImage} alt="preview" className="w-full h-full object-cover" /> : <span className="text-2xl opacity-30 text-white">🖼️</span>}
            </div>
            <button onClick={takePhoto} className="w-20 h-20 rounded-full border-[6px] border-white/20 p-1 active:scale-95 transition-transform">
              <div className="w-full h-full rounded-full bg-white shadow-inner text-white"></div>
            </button>
            <button className="w-14 h-14 flex items-center justify-center text-2xl text-white/40">🔄</button>
          </div>
        </div>
      </div>
    );
  }

  // [B] 결과 화면 (수정됨: 환경 정보 박스 추가)
  if (viewMode === "result") {
    return (
      <div className="fixed inset-0 bg-white flex justify-center overflow-hidden font-sans z-[110]">
        <div className="relative w-full max-w-[420px] h-full flex flex-col shadow-2xl text-black">
          
          {/* 헤더 */}
          <div className="px-5 pt-3 border-b border-gray-50 sticky top-0 bg-white z-20">
            <div className="flex justify-between items-center text-[13px] font-bold mb-4">
              <span>9:41</span><div className="flex gap-1">📶🔋</div>
            </div>
            <div className="flex items-center justify-between mb-4">
              <button onClick={() => { setViewMode("home"); setCapturedImage(null); }} className="text-2xl font-bold text-black">✕</button>
              <h2 className="font-bold text-[17px] text-black">에기를 물어봐</h2>
              <div className="flex items-center gap-1">
                <span className="text-xs">📍</span>
                <span className="text-[10px] text-gray-500 text-right leading-tight text-black">
                    {environmentData?.location_name || "위치 정보 없음"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-5 pt-4 pb-32 no-scrollbar bg-white">
            
            {/* 1. [추가] 환경 정보 카드 (결과 화면 최상단에 배치) */}
            <div className="mb-6">
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

                    <div className="grid grid-cols-3 gap-3">
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
                </div>
                )}
            </div>

            {/* 2. 분석된 이미지 */}
            <div className="w-full h-44 bg-[#00694e] rounded-[30px] mb-6 shadow-lg overflow-hidden relative flex items-center justify-center">
               {capturedImage && <img src={capturedImage} alt="" className="w-full h-full object-cover opacity-50 mix-blend-overlay" />}
               <div className="absolute inset-0 bg-[#00694e] opacity-40"></div>
            </div>

            {/* 3. 분석 멘트 */}
            <div className="bg-gray-50 rounded-[30px] p-6 flex items-center gap-5 mb-10 border border-gray-100 shadow-sm text-black">
              <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center flex-shrink-0 text-black border border-gray-100 overflow-hidden">
                <img src={wangpandaImg} alt="Panda" className="w-full h-full object-cover" />
              </div>
              <p className="text-[15px] text-gray-700 font-medium leading-relaxed text-black">
                "현재 바다 색깔은 <span className="font-bold text-[#00694e]">초록색</span> 을 띄고 있습니다."
              </p>
            </div>

            {/* 4. 추천 에기 리스트 */}
            <h3 className="font-bold text-[16px] mb-4 text-black">추천 에기 리스트</h3>
            <div className="space-y-8 animate-in fade-in duration-500 text-black">
            {resultRecEgis.map((egi) => (
                <div key={egi.id} className="flex flex-col items-center text-black">
                    <div className="w-full h-[180px] bg-gray-50 rounded-2xl mb-3 overflow-hidden border border-gray-100 flex items-center justify-center p-4">
                        <img src={egi.img} alt={egi.name} className="w-full h-full object-contain" />
                    </div>
                    <div className="w-full text-left px-1 text-black">
                        <h4 className="font-black text-[15px] mb-1 text-gray-900 text-black">{egi.name}</h4>
                        <p className="text-[13px] text-gray-500 text-black">"{egi.desc}"</p>
                    </div>
                </div>
            ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // [C] 홈 메인 화면
  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        
        <TopBar user={user} onNavigate={onNavigate} />

        <div className={`flex-1 overflow-y-auto no-scrollbar transition-all duration-300 ${isModalOpen ? 'brightness-50' : ''}`} style={{ paddingBottom: '200px' }}>
          
          {/* 배너 영역 */}
          <div className="px-5 mt-4">
            <div className="relative w-full h-[170px] rounded-[28px] overflow-hidden shadow-sm">
              <img src={pandaBanner} alt="Banner" className="w-full h-full object-cover" />
            </div>
          </div>

          {/* 환경 정보 카드 (홈 화면용) */}
          <div className="px-5 mt-6 relative z-30 text-black"> 
             <div className="flex justify-between items-center mb-3">
              <h3 className="font-bold text-[17px] text-black font-sans">
                현재 낚시 환경 🌊
              </h3>
              <button
                onClick={fetchEnvironmentData}
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

                <div className="grid grid-cols-3 gap-3">
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
            <h3 className="font-bold text-[17px] mb-4 text-black font-sans">추천 에기 〉</h3>
            {recommendedEgis.length > 0 ? (
                <div className="flex gap-4 overflow-x-auto no-scrollbar pb-6">
                {recommendedEgis.map((egi) => (
                    <div key={egi.egi_id} className="min-w-[140px]" onClick={() => onNavigate('egi-detail', egi)}>
                        <div className="w-[140px] h-[140px] bg-gray-50 rounded-[24px] overflow-hidden border border-gray-100 shadow-sm relative">
                            <img src={egi.image_url || defaultEgiImg} alt={egi.name} className="w-full h-full object-cover" onError={(e) => { e.target.src = defaultEgiImg; }} />
                        </div>
                        <p className="text-[13px] font-bold mt-2 text-center text-gray-800 truncate px-1">{egi.name}</p>
                    </div>
                ))}
                </div>
            ) : (
                <div className="text-center py-10 text-gray-400 bg-gray-50 rounded-2xl"><p className="text-xs">등록된 추천 에기가 없습니다.</p></div>
            )}
          </div>
        </div>

        <BottomTab activeTab="home" onNavigate={onNavigate} onCameraClick={() => setIsModalOpen(true)} />

        {isModalOpen && (
          <div className="absolute inset-0 z-[100] flex items-end justify-center px-4 pb-12 transition-all">
            <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={() => setIsModalOpen(false)}></div>
            <div className="relative w-full bg-white rounded-[32px] overflow-hidden shadow-2xl p-8 animate-in slide-in-from-bottom duration-300">
              <p className="text-center text-gray-800 font-bold mb-8 text-[15px]">입력할 방법을 선택해주세요.</p>
              <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept="image/*" />
              <div className="flex justify-around items-center">
                <button onClick={() => { setViewMode("camera"); setIsModalOpen(false); }} className="flex flex-col items-center gap-3">
                  <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center text-3xl shadow-sm border border-gray-100">📷</div>
                  <span className="text-[13px] font-bold text-gray-600">카메라</span>
                </button>
                <button onClick={() => fileInputRef.current.click()} className="flex flex-col items-center gap-3">
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