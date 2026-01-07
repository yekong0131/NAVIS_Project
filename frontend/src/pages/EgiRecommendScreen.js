import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import TopBar from "../components/TopBar";
import defaultEgiImg from "../assets/ndchjegi.jpg";
import wangpandaImg from "../assets/login_panda.png";

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Base64 -> File 변환 헬퍼
const dataURLtoFile = (dataurl, filename) => {
    let arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1],
    bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
    while(n--){ u8arr[n] = bstr.charCodeAt(n); }
    return new File([u8arr], filename, {type:mime});
};

// 위치 가져오기 헬퍼
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

const EgiRecommendScreen = ({ onNavigate, user, savedState, onSaveState, fromPage, initialMode }) => {
    // 1. 초기 모드 설정
    const [viewMode, setViewMode] = useState(() => {
        if (savedState) return "result";
        return initialMode === 'gallery' ? 'gallery' : 'camera';
    });

    const [capturedImage, setCapturedImage] = useState(savedState?.image || null);
    const [analysisResult, setAnalysisResult] = useState(savedState?.result || null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    
    // [추가] 디버그 모드 토글
    const [showDebug, setShowDebug] = useState(false);

    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const streamRef = useRef(null);
    const fileInputRef = useRef(null);
    
    const hasOpenedGallery = useRef(false);
    const isMounted = useRef(true);

    useEffect(() => {
        isMounted.current = true;
        return () => { isMounted.current = false; };
    }, []);

    // === 카메라 제어 함수 ===
    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }
        if (videoRef.current) videoRef.current.srcObject = null;
    };

    const startCamera = async () => {
        stopCamera();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "environment" },
            });
            
            if (!isMounted.current || viewMode !== 'camera') {
                stream.getTracks().forEach(track => track.stop());
                return;
            }
            streamRef.current = stream;
            if (videoRef.current) videoRef.current.srcObject = stream;
        } catch (err) {
            console.error(err);
            if (isMounted.current && viewMode === 'camera') {
                alert("카메라 권한이 필요하거나 지원하지 않는 기기입니다.");
            }
        }
    };

    useEffect(() => {
        if (viewMode === "camera") startCamera();
        else stopCamera();
        return () => stopCamera();
    }, [viewMode]);

    useEffect(() => {
        if (viewMode === 'gallery' && !hasOpenedGallery.current && !savedState) {
            hasOpenedGallery.current = true;
            setTimeout(() => { if (fileInputRef.current) fileInputRef.current.click(); }, 100);
        }
    }, [viewMode, savedState]);

    // === 이벤트 핸들러 ===
    const handleShutterClick = () => {
        if (viewMode === 'gallery') setViewMode('camera');
        else takePhoto();
    };

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
            processCapture(imageData);
        }
    };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setCapturedImage(reader.result);
                processCapture(reader.result);
            };
            reader.readAsDataURL(file);
        }
        event.target.value = ''; 
    };

    const handleGalleryClick = () => {
        if (viewMode === 'camera') setViewMode('gallery');
        if (fileInputRef.current) fileInputRef.current.click();
    };

    const handleClose = () => {
        stopCamera();
        onNavigate(fromPage || 'home'); 
    };

    const processCapture = async (imageDataUrl) => {
        stopCamera();
        setIsAnalyzing(true);

        try {
            const location = await getUserLocation();
            const imageFile = dataURLtoFile(imageDataUrl, "capture.png");

            const formData = new FormData();
            formData.append("image", imageFile);
            formData.append("lat", location.lat);
            formData.append("lon", location.lon);
            formData.append("target_fish", "쭈갑");

            const token = localStorage.getItem('authToken');

            const response = await axios.post(`${API_URL}/egi/recommend/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': `Token ${token}`,
                }
            });

            // 응답 상태에 따른 분기 처리
            if (response.data.status === 'success') {
                const resultData = response.data.data;
                setAnalysisResult(resultData);
                if (onSaveState) onSaveState({ result: resultData, image: imageDataUrl });
                
                // 성공했을 때만 결과 화면으로 이동
                setViewMode("result"); 
            
            } else if (response.data.status === 'fail') {
                // 실패 시 (물 미검출)
                alert(response.data.message || "바다를 인식하지 못했습니다. 다시 촬영해주세요.");
                setViewMode("camera"); // 다시 카메라 모드로
                startCamera(); // 카메라 재시작
            }
        } catch (err) {
            console.error("분석 실패:", err);
            alert("분석 중 오류가 발생했습니다.\n" + (err.response?.data?.detail || err.message));
            setViewMode("camera");
        } finally {
            setIsAnalyzing(false);
        }
    };

    // [A] 로딩 화면
    if (isAnalyzing) {
        return (
            <div className="fixed inset-0 bg-white flex justify-center items-center z-[110]">
                <div className="flex flex-col items-center animate-pulse">
                    <div className="w-20 h-20 bg-gray-200 rounded-full mb-4"></div>
                    <h2 className="text-xl font-bold text-gray-800">물색을 분석 중입니다...</h2>
                    <p className="text-sm text-gray-500 mt-2">잠시만 기다려주세요 🌊</p>
                </div>
            </div>
        );
    }

    // [B] 결과 화면
    if (viewMode === "result" && analysisResult) {
        const aiEnv = analysisResult.environment || {};
        const aiRecs = analysisResult.recommendations || [];
        const debugInfo = analysisResult.debug_info || {}; // 디버그 정보

        const aiWater = analysisResult.analysis_result?.water_color || "분석 중...";
        const aiConf = analysisResult.analysis_result?.confidence || 0;

        const waterColorKo = {
            "Muddy": "탁함", "clear": "맑음", "medium": "보통", 
            "VeryMuddy": "매우 탁함", "VeryClear": "매우 맑음"
        }[aiWater] || aiWater;

        return (
            <div className="fixed inset-0 bg-white flex justify-center overflow-hidden font-sans z-[110]">
                <div className="relative w-full max-w-[420px] h-full flex flex-col shadow-2xl text-black">
                    {/* 상단 헤더 */}
                    <div className="px-5 pt-3 border-b border-gray-50 sticky top-0 bg-white z-20">
                        <div className="flex justify-between items-center text-[13px] font-bold mb-4">
                            <span>9:41</span><div className="flex gap-1">📶🔋</div>
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <button onClick={handleClose} className="text-2xl font-bold text-black">✕</button>
                            <h2 className="font-bold text-[17px] text-black">AI 분석 결과</h2>
                            <div className="flex items-center gap-1">
                                <span className="text-xs">📍</span>
                                <span className="text-[10px] text-gray-500 text-right leading-tight text-black">
                                    {aiEnv.location_name || "위치 정보 없음"}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto px-5 pt-4 pb-32 no-scrollbar bg-white">
                        {/* 1. 환경 정보 카드 */}
                        <div className="mb-6">
                            <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-[20px] p-4 shadow-sm border border-blue-100">
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                                        <div className="text-xl mb-1">🌊</div>
                                        <p className="text-[10px] text-gray-500 font-medium mb-1">물때</p>
                                        <p className="text-[13px] font-bold text-gray-800">{aiEnv.tide+'물' || '-'}</p>
                                    </div>
                                    <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                                        <div className="text-xl mb-1">💨</div>
                                        <p className="text-[10px] text-gray-500 font-medium mb-1">풍속</p>
                                        <p className="text-[13px] font-bold text-gray-800">{aiEnv.wind_speed ? aiEnv.wind_speed + 'm/s' : '-'}</p>
                                    </div>
                                    <div className="bg-white rounded-xl p-3 text-center shadow-sm">
                                        <div className="text-xl mb-1">🌡️</div>
                                        <p className="text-[10px] text-gray-500 font-medium mb-1">수온</p>
                                        <p className="text-[13px] font-bold text-gray-800">{aiEnv.water_temp ? aiEnv.water_temp + '°C' : '-'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        {/* 1.5 추천 색상 표시  */}
                        <div className="flex flex-col items-center justify-center mb-8 animate-pulse">
                            <span className="text-xs font-bold text-blue-600 bg-blue-50 px-3 py-1 rounded-full mb-2 border border-blue-100">
                                ✨ AI 분석 오늘의 추천 컬러
                            </span>
                            <h1 className="text-4xl font-black text-gray-800 tracking-tight drop-shadow-sm">
                                {aiRecs.length > 0 ? aiRecs[0].color_name : "분석 중..."}
                            </h1>
                        </div>
                        {/* 2. 사진 & 물색 */}
                        <div className="w-full h-44 bg-gray-100 rounded-[30px] mb-6 shadow-lg overflow-hidden relative flex items-center justify-center">
                            {capturedImage && <img src={capturedImage} alt="" className="w-full h-full object-cover opacity-90" />}
                            <div className="absolute bottom-3 right-3 bg-black/60 px-3 py-1 rounded-full backdrop-blur-sm border border-white/20">
                                <span className="text-white text-xs font-bold">
                                    💧 물색: {waterColorKo} 
                                </span>
                            </div>
                        </div>
                        

                        {/* 3. 코멘트 */}
                        <div className="bg-gray-50 rounded-[30px] p-6 flex items-center gap-5 mb-10 border border-gray-100 shadow-sm text-black">
                            <div className="w-16 h-16 rounded-full bg-white flex items-center justify-center flex-shrink-0 text-black border border-gray-100 overflow-hidden">
                                <img src={wangpandaImg} alt="Panda" className="w-full h-full object-cover" />
                            </div>
                            <p className="text-[14px] text-gray-700 font-medium leading-relaxed text-black">
                                {aiRecs.length > 0 ? `"${aiRecs[0].reason}"` : "분석 결과에 맞는 에기를 찾고 있습니다..."}
                            </p>
                        </div>

                        {/* 4. 추천 리스트 */}
                        <h3 className="font-bold text-[16px] mb-4 text-black">AI 추천 에기</h3>
                        <div className="space-y-6 text-black mb-8">
                            {aiRecs.map((egi, index) => (
                                <div 
                                    key={index}
                                    onClick={() => onNavigate('egi-detail', { ...egi, fromPage: 'egi-recommendation' })}
                                    className="flex flex-col items-center text-black bg-white rounded-2xl p-4 border border-gray-100 shadow-sm cursor-pointer active:scale-95 transition-transform"
                                >
                                    <div className="w-full h-[160px] bg-white rounded-xl mb-3 overflow-hidden flex items-center justify-center relative border border-gray-50">
                                        <div className="absolute top-2 left-2 bg-blue-600 text-white w-7 h-7 flex items-center justify-center rounded-full font-bold text-xs shadow-md z-10">
                                            {index + 1}
                                        </div>
                                        <img 
                                            src={egi.image_url || defaultEgiImg} 
                                            alt={egi.name} 
                                            className="w-full h-full object-contain p-2" 
                                            onError={(e) => { e.target.src = defaultEgiImg; }} 
                                        />
                                    </div>
                                    <div className="w-full text-left px-1 text-black">
                                        <h4 className="font-bold text-[15px] mb-1 text-gray-900 line-clamp-2 leading-tight min-h-[42px]">{egi.name}</h4>
                                        <div className="flex flex-wrap gap-2 mt-1">
                                            <span className="text-[11px] bg-blue-50 text-blue-600 px-2 py-1 rounded font-bold">{egi.color_name}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* 5. [신규] AI 분석 과정 보기 (디버그 모드) */}
                        {debugInfo.yolo_image && (
                            <div className="border-t border-gray-100 pt-6 mb-10">
                                <button 
                                    onClick={() => setShowDebug(!showDebug)}
                                    className="w-full flex justify-between items-center bg-gray-50 p-4 rounded-xl text-sm font-bold text-gray-700 hover:bg-gray-100 transition-colors"
                                >
                                    <span>🤖 AI 분석 과정 보기 (개발자용)</span>
                                    <span>{showDebug ? "▲" : "▼"}</span>
                                </button>

                                {showDebug && debugInfo.yolo_image && (
                                    <div className="mt-4 space-y-6 animate-in slide-in-from-top duration-300">
                                        
                                        {/* Step 1: YOLO 디텍팅 */}
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="bg-green-100 text-green-700 text-[10px] font-bold px-2 py-1 rounded">Step 1</span>
                                                <h4 className="font-bold text-sm text-gray-800">YOLO 물체 인식</h4>
                                            </div>
                                            <div className="rounded-xl overflow-hidden border border-green-200 relative">
                                                <img src={debugInfo.yolo_image} alt="YOLO Result" className="w-full h-auto object-cover" />
                                                <div className="absolute bottom-0 left-0 right-0 bg-green-500/80 text-white text-[10px] p-1 px-3">
                                                    바다(Water) 영역을 찾아 초록색 박스로 표시했습니다.
                                                </div>
                                            </div>
                                        </div>

                                        {/* Step 2: 물색 분석 */}
                                        <div className="flex gap-4">
                                            <div className="w-1/2">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="bg-blue-100 text-blue-700 text-[10px] font-bold px-2 py-1 rounded">Step 2</span>
                                                    <h4 className="font-bold text-sm text-gray-800">색상 분석</h4>
                                                </div>
                                                <div className="rounded-xl overflow-hidden border border-blue-200 aspect-square relative">
                                                    <img src={debugInfo.crop_image} alt="Cropped Water" className="w-full h-full object-cover" />
                                                </div>
                                            </div>
                                            <div className="w-1/2 flex flex-col justify-center text-xs space-y-2">
                                                <p className="text-gray-500">이 부분을 잘라내어<br/>CNN 모델에 입력했습니다.</p>
                                                <div className="bg-gray-100 p-2 rounded-lg">
                                                    <span className="block font-bold text-gray-700">AI 예측 결과:</span>
                                                    <span className="text-blue-600 font-bold text-lg uppercase">{debugInfo.ai_prediction}</span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Step 3: 매핑 결과 */}
                                        <div>
                                            <div className="flex items-center gap-2 mb-2">
                                                <span className="bg-purple-100 text-purple-700 text-[10px] font-bold px-2 py-1 rounded">Step 3</span>
                                                <h4 className="font-bold text-sm text-gray-800">에기 매핑</h4>
                                            </div>
                                            <div className="bg-gray-50 p-3 rounded-xl border border-dashed border-gray-300 text-xs text-gray-600 leading-relaxed">
                                                <p>1. AI가 물색을 <strong>"{debugInfo.ai_prediction}"</strong>으로 판단.</p>
                                                <p>2. 추천 에기 색상: <strong>"{aiRecs[0]?.color_name || '?'}"</strong></p>
                                                <p>3. DB에서 해당 색상 ID를 가진 에기 검색 완료.</p>
                                            </div>
                                        </div>
                                        {/* [추가] 4. 디버그용 프롬프트 출력 (관리자 확인용)            */}
                                        {/* debugInfo가 있고, step4_sllm_prompt가 존재할 때만 표시됨  */}
                                        {/* ======================================================== */}
                                        {debugInfo && debugInfo.step4_sllm_prompt && (
                                            <div className="mt-6 p-4 bg-gray-900 rounded-xl text-left border border-gray-700 overflow-hidden">
                                                <div className="flex justify-between items-center mb-2">
                                                    <span className="text-xs font-bold text-yellow-400">📜 LLM 입력 프롬프트 (Debug)</span>
                                                </div>
                                                <pre className="text-[10px] text-gray-300 whitespace-pre-wrap font-mono leading-tight break-all">
                                                    {debugInfo.step4_sllm_prompt}
                                                </pre>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                    
                </div>
            </div>
        );
    }

    // [C] 입력 모드 화면
    return (
        <div className="fixed inset-0 bg-slate-900 flex justify-center items-center z-[100]">
            <div className="relative w-full max-w-[420px] h-full bg-black flex flex-col">
                {/* [추가] 최상단 TopBar */}
                <TopBar user={user} onNavigate={onNavigate} />

                <div className="px-6 pt-12 flex justify-between items-center z-10 text-white">
                    <button onClick={handleClose} className="text-2xl font-bold text-white">✕</button>
                    <span className="text-sm font-medium tracking-widest uppercase font-bold text-gray-400">AI Analysis</span>
                    <div className="w-6 h-6"></div>
                </div>
                
                {/* 뷰파인더 영역 */}
                <div className="flex-1 relative flex items-center justify-center bg-gray-900 overflow-hidden">
                    {viewMode === 'camera' ? (
                        <>
                            <video ref={videoRef} autoPlay playsInline className="absolute inset-0 w-full h-full object-cover" />
                            <canvas ref={canvasRef} className="hidden" />
                            <div className="absolute inset-0 border-2 border-white/30 m-8 rounded-3xl pointer-events-none flex items-center justify-center">
                                <p className="text-white/70 text-xs bg-black/50 px-3 py-1 rounded-full">바다를 비춰주세요</p>
                            </div>
                        </>
                    ) : (
                        <div className="text-gray-500 flex flex-col items-center">
                            <span className="text-4xl mb-2">🖼️</span>
                            <span className="text-sm">사진을 선택해주세요</span>
                        </div>
                    )}
                </div>

                <div className="h-44 bg-black flex items-center justify-between px-10 pb-10 relative text-white">
                    <button onClick={handleGalleryClick} className="w-14 h-14 flex items-center justify-center rounded-full bg-gray-800 active:bg-gray-700">
                        <span className="text-2xl">🖼️</span>
                    </button>
                    <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept="image/*" />

                    <button onClick={handleShutterClick} className="w-20 h-20 rounded-full border-[6px] border-white/20 p-1 active:scale-95 transition-transform">
                        <div className={`w-full h-full rounded-full shadow-inner transition-colors ${viewMode === 'gallery' ? 'bg-red-500' : 'bg-white'} flex items-center justify-center`}>
                            {viewMode === 'gallery' && <span className="text-[10px] font-bold text-white">Camera</span>}
                        </div>
                    </button>
                    
                    <div className="w-14 h-14"></div>
                </div>
            </div>
        </div>
    );
};

export default EgiRecommendScreen;