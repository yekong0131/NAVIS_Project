import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

// API 주소
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const VoiceRecordScreen = ({ onNavigate }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState(0); // 0 ~ 100

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  
  // 오디오 시각화용 Ref
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const animationFrameRef = useRef(null);

  // 컴포넌트 해제 시 정리
  useEffect(() => {
    return () => {
        cancelAnimationFrame(animationFrameRef.current);
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close();
        }
    };
  }, []);

  const getSupportedMimeType = () => {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return '';
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // ----------------------------------------------------
      // 오디오 시각화 (볼륨 미터) 설정
      // ----------------------------------------------------
      if (!audioContextRef.current) {
          audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const audioCtx = audioContextRef.current;

      // 브라우저 정책으로 중지된 오디오 엔진 깨우기
      if (audioCtx.state === 'suspended') {
          await audioCtx.resume();
      }

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      
      analyserRef.current = analyser;
      const bufferLength = analyser.frequencyBinCount;
      dataArrayRef.current = new Uint8Array(bufferLength);
      
      detectVolume();
      // ----------------------------------------------------

      const mimeType = getSupportedMimeType();
      const options = mimeType ? { mimeType } : {};
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = handleStop;
      mediaRecorderRef.current.start(100);
      setIsRecording(true);

    } catch (err) {
      console.error("마이크 접근 실패:", err);
      alert("마이크를 사용할 수 없습니다. 권한 설정을 확인해주세요.");
    }
  };

  // 실시간 볼륨 감지
  const detectVolume = () => {
      if (!analyserRef.current || !dataArrayRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArrayRef.current);
      
      let sum = 0;
      const length = dataArrayRef.current.length;
      for (let i = 0; i < length; i++) {
          sum += dataArrayRef.current[i];
      }
      const average = sum / length;
      
      // 시각화 효과를 위해 값을 좀 키움 (최대 100)
      const normalizedVolume = Math.min(100, average * 2.5); 
      setVolumeLevel(normalizedVolume);

      animationFrameRef.current = requestAnimationFrame(detectVolume);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setVolumeLevel(0);
      cancelAnimationFrame(animationFrameRef.current);
      
      if (mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
    }
  };

  const handleStop = async () => {
    setTimeout(async () => {
        if (audioChunksRef.current.length === 0) return;
        setIsAnalyzing(true);
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioFile = new File([audioBlob], "recording.webm", { type: "audio/webm" });
        
        const formData = new FormData();
        formData.append('audio', audioFile);

        try {
            const response = await axios.post(`${API_BASE_URL}/diaries/analyze/`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            if (onNavigate) onNavigate('write', response.data);

        } catch (error) {
            console.error("분석 실패:", error);
            const msg = error.response?.data?.error || "분석 중 오류가 발생했습니다.";
            alert(msg);
            setIsAnalyzing(false);
        }
    }, 500);
  };

  return (
    <div className="fixed inset-0 bg-slate-900 flex justify-center items-center z-50 font-sans">
        <div className="relative w-full max-w-[420px] h-full bg-slate-900 flex flex-col text-white shadow-2xl overflow-hidden">
            
            {/* 닫기 버튼 */}
            <div className="absolute top-0 right-0 p-6 pt-12 z-[60]">
                <button 
                    onClick={() => {
                        if (isRecording) stopRecording();
                        onNavigate('diary');
                    }} 
                    className="p-4 text-gray-400 hover:text-white cursor-pointer"
                >
                    <span className="text-2xl font-bold">✕</span>
                </button>
            </div>

            {/* 메인 영역 */}
            <div className="flex-1 flex flex-col items-center justify-center -mt-10">
                {isAnalyzing ? (
                    <div className="flex flex-col items-center animate-pulse">
                        <span className="text-5xl mb-6">🧠</span>
                        <h2 className="text-xl font-bold text-indigo-300">분석 중입니다...</h2>
                        <p className="text-sm text-gray-400 mt-2">조과 내용을 정리하고 있어요</p>
                    </div>
                ) : (
                    <>
                        {/* 마이크 버튼 & 시각화 효과 */}
                        <div className={`relative w-40 h-40 rounded-full flex items-center justify-center transition-all duration-200 ${isRecording ? 'bg-gray-800' : 'bg-gray-800'}`}>
                            
                            {/* 볼륨에 따라 커지는 초록색 아우라 */}
                            {isRecording && (
                                <div 
                                    className="absolute inset-0 rounded-full bg-green-500/30 blur-xl transition-all duration-75"
                                    style={{ transform: `scale(${1 + volumeLevel / 40})` }}
                                ></div>
                            )}

                            <button 
                                onClick={isRecording ? stopRecording : startRecording}
                                className={`relative z-10 w-28 h-28 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 ${isRecording ? 'bg-red-500 hover:bg-red-600' : 'bg-indigo-600 hover:bg-indigo-500'}`}
                            >
                                <span className="text-5xl">{isRecording ? '⬛' : '🎤'}</span>
                            </button>
                        </div>
                        
                        {/* 볼륨 막대 그래프 */}
                        <div className="w-64 h-1.5 bg-gray-700 rounded-full mt-8 overflow-hidden">
                            <div 
                                className={`h-full transition-all duration-75 ease-out ${volumeLevel > 0 ? 'bg-green-400 shadow-[0_0_10px_#4ade80]' : 'bg-transparent'}`}
                                style={{ width: `${volumeLevel}%` }}
                            ></div>
                        </div>

                        <h2 className="text-2xl font-bold mt-6 mb-2">
                            {isRecording ? "듣고 있어요..." : "터치하여 말하기"}
                        </h2>
                        
                        {/* ⭐ 다시 돌아온 예시 문구! */}
                        {!isRecording && (
                            <div className="bg-white/5 rounded-2xl p-5 mx-8 mt-4 border border-white/10 animate-fade-in-up">
                                <p className="text-gray-300 text-sm text-center leading-relaxed">
                                    <span className="text-indigo-300 font-bold">"오늘 삼봉항에서 쭈꾸미 20마리 잡았어"</span>
                                    <br/>처럼 말해보세요.
                                </p>
                            </div>
                        )}

                        {/* 녹음 중일 때 상태 메시지 */}
                        {isRecording && (
                             <p className="text-sm text-gray-400 mt-2 animate-pulse">
                                {volumeLevel < 5 ? "좀 더 크게 말씀해주세요 📢" : "목소리가 잘 들립니다! 👌"}
                             </p>
                        )}
                    </>
                )}
            </div>
        </div>
    </div>
  );
};

export default VoiceRecordScreen;