import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TopBar from '../components/TopBar';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

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

const DiaryWriteScreen = ({ onNavigate, initialDiary, user }) => {
  const [loading, setLoading] = useState(false);
  const [egiColors, setEgiColors] = useState([]); 
  const [isEgiModalOpen, setIsEgiModalOpen] = useState(false);
  const [isPortModalOpen, setIsPortModalOpen] = useState(false);
  const [portSearchQuery, setPortSearchQuery] = useState("");
  const [portSearchResults, setPortSearchResults] = useState([]);
  const [isSearchingPort, setIsSearchingPort] = useState(false);
  const [currentLogId, setCurrentLogId] = useState(null);

  useEffect(() => {
    const fetchEgiColors = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/egi/colors/`);
        if (response.data) setEgiColors(response.data);
      } catch (error) {
        setEgiColors([
          { color_id: 1, color_name: '빨강' }, { color_id: 2, color_name: '주황' },
          { color_id: 3, color_name: '노랑' }, { color_id: 4, color_name: '초록' },
          { color_id: 5, color_name: '파랑' }, { color_id: 6, color_name: '보라' },
          { color_id: 7, color_name: '핑크' }, { color_id: 8, color_name: '갈색' },
          { color_id: 9, color_name: '무지개' },{ color_id: 10, color_name: '기타' },
        ]);
      }
    };
    fetchEgiColors();

    if (initialDiary) {
        let formattedDate = new Date().toISOString().slice(0, 16);
        if (initialDiary.fishing_date) {
            const d = new Date(initialDiary.fishing_date);
            const offset = d.getTimezoneOffset() * 60000;
            formattedDate = new Date(d.getTime() - offset).toISOString().slice(0, 16);
        }

        const existingImages = initialDiary.images 
            ? initialDiary.images.map(img => ({
                type: 'server',
                id: img.image_id,
                url: img.image_url,
                file: null
              }))
            : [];

        const loadedLog = {
            id: initialDiary.diary_id || Date.now(),
            date: formattedDate,
            location: initialDiary.location_name || '',
            lat: initialDiary.lat,
            lon: initialDiary.lon,
            boatName: initialDiary.boat_name || '',
            content: initialDiary.content || '',
            
            catches: initialDiary.catches && initialDiary.catches.length > 0 
                ? initialDiary.catches.map(c => ({
                    id: c.catch_id || Date.now() + Math.random(),
                    fishType: c.fish_name,
                    count: c.count
                  }))
                : [{ id: Date.now(), fishType: '갑오징어', count: '' }],
            
            selectedEgis: initialDiary.used_egis 
                ? initialDiary.used_egis.map(e => ({
                    color_id: e.color_id,
                    color_name: e.color_name
                  }))
                : [],
            
            images: existingImages,
            deletedImageIds: [],
            isEditMode: !!initialDiary.diary_id
        };

        setLogs([loadedLog]);
    }
  }, [initialDiary]);

  const [logs, setLogs] = useState([
    {
      id: Date.now(),
      date: new Date().toISOString().slice(0, 16),
      location: '', 
      lat: null,    
      lon: null,    
      boatName: '', 
      catches: [{ id: Date.now() + 1, fishType: '갑오징어', count: '' }],
      selectedEgis: [], 
      content: '',
      images: [],
      deletedImageIds: [],
      isEditMode: false
    }
  ]);

  const addLog = () => {
    setLogs([
      ...logs,
      {
        id: Date.now(),
        date: new Date().toISOString().slice(0, 16),
        location: '',
        lat: null,
        lon: null,
        boatName: '',
        catches: [{ id: Date.now() + 1, fishType: '갑오징어', count: '' }],
        selectedEgis: [],
        content: '',
        images: [],
        deletedImageIds: [],
        isEditMode: false
      }
    ]);
  };

  const removeLog = (id) => {
    if (logs.length === 1) {
      alert("최소 1개의 일지는 작성해야 합니다.");
      return;
    }
    setLogs(logs.filter(log => log.id !== id));
  };

  const updateLog = (id, field, value) => {
    setLogs(logs.map(log => 
      log.id === id ? { ...log, [field]: value } : log
    ));
  };

  const addCatchRow = (logId) => {
    setLogs(logs.map(log => {
      if (log.id === logId) {
        return {
          ...log,
          catches: [...log.catches, { id: Date.now(), fishType: '쭈꾸미', count: '' }]
        };
      }
      return log;
    }));
  };

  const removeCatchRow = (logId, catchId) => {
    setLogs(logs.map(log => {
      if (log.id === logId) {
        if (log.catches.length === 1) return log;
        return {
          ...log,
          catches: log.catches.filter(c => c.id !== catchId)
        };
      }
      return log;
    }));
  };

  const updateCatchRow = (logId, catchId, field, value) => {
    setLogs(logs.map(log => {
      if (log.id === logId) {
        return {
          ...log,
          catches: log.catches.map(c => 
            c.id === catchId ? { ...c, [field]: value } : c
          )
        };
      }
      return log;
    }));
  };

  const openEgiModal = (logId) => {
    setCurrentLogId(logId);
    setIsEgiModalOpen(true);
  };

  const toggleEgiSelection = (color) => {
    setLogs(logs.map(log => {
      if (log.id === currentLogId) {
        const isSelected = log.selectedEgis.some(e => e.color_id === color.color_id);
        let newEgis;
        if (isSelected) {
          newEgis = log.selectedEgis.filter(e => e.color_id !== color.color_id);
        } else {
          newEgis = [...log.selectedEgis, color];
        }
        return { ...log, selectedEgis: newEgis };
      }
      return log;
    }));
  };

  const openPortModal = (logId) => {
    setCurrentLogId(logId);
    setPortSearchQuery("");
    setPortSearchResults([]);
    setIsPortModalOpen(true);
  };

  const searchPorts = async () => {
    if (!portSearchQuery.trim()) return;
    setIsSearchingPort(true);
    try {
        const response = await axios.get(`${API_BASE_URL}/ports/search/`, {
            params: { query: portSearchQuery }
        });
        setPortSearchResults(response.data);
    } catch (error) {
        console.error("항구 검색 실패:", error);
        alert("검색 중 오류가 발생했습니다.");
    } finally {
        setIsSearchingPort(false);
    }
  };

  const selectPort = (port) => {
    setLogs(logs.map(log => {
        if (log.id === currentLogId) {
            return {
                ...log,
                location: port.port_name,
                lat: port.lat,
                lon: port.lon
            };
        }
        return log;
    }));
    setIsPortModalOpen(false);
  };

  const handleFileChange = (e, id) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    const newImages = files.map(file => ({
        type: 'local',
        id: Date.now() + Math.random(),
        url: URL.createObjectURL(file),
        file: file
    }));
    
    setLogs(logs.map(log => {
        if (log.id === id) {
            return { ...log, images: [...log.images, ...newImages] };
        }
        return log;
    }));
  };

  const handleRemoveImage = (logId, imageIndex) => {
    setLogs(logs.map(log => {
        if (log.id === logId) {
            const targetImage = log.images[imageIndex];
            
            let newDeletedIds = log.deletedImageIds || [];
            if (targetImage.type === 'server') {
                newDeletedIds = [...newDeletedIds, targetImage.id];
            }

            const newImages = log.images.filter((_, idx) => idx !== imageIndex);

            return {
                ...log,
                images: newImages,
                deletedImageIds: newDeletedIds
            };
        }
        return log;
    }));
  };

  const handleSave = async () => {
    if (loading) return;
    
    for (const log of logs) {
        if (!log.location.trim()) {
            alert("위치(항구명)를 선택해주세요.");
            return;
        }
    }

    setLoading(true);
    const token = localStorage.getItem('authToken');

    try {
      const uploadPromises = logs.map((log) => {
        const formData = new FormData();

        formData.append('fishing_date', new Date(log.date).toISOString());
        formData.append('location_name', log.location);
        
        if (log.lat && log.lon) {
            formData.append('lat', log.lat);
            formData.append('lon', log.lon);
        }
        if (log.boatName) {
            formData.append('boat_name', log.boatName);
        }

        formData.append('content', log.content);

        const egiIds = log.selectedEgis.map(e => e.color_id);
        if (egiIds.length > 0) {
            formData.append('used_egi_colors', JSON.stringify(egiIds));
        }

        const catchData = log.catches.map(c => ({
            fish_name: c.fishType,
            count: parseInt(c.count) || 0
        }));
        formData.append('catches', JSON.stringify(catchData));

        const localImages = log.images.filter(img => img.type === 'local');
        localImages.forEach((imgObj) => {
            formData.append('images', imgObj.file);
        });

        if (log.isEditMode && log.deletedImageIds.length > 0) {
            formData.append('delete_image_ids', JSON.stringify(log.deletedImageIds));
        }

        if (log.isEditMode) {
            return axios.patch(`${API_BASE_URL}/diaries/${log.id}/`, formData, {
                headers: {
                    Authorization: `Token ${token}`,
                    'Content-Type': 'multipart/form-data',
                }
            });
        } else {
            return axios.post(`${API_BASE_URL}/diaries/`, formData, {
                headers: {
                    Authorization: `Token ${token}`,
                    'Content-Type': 'multipart/form-data',
                }
            });
        }
      });

      await Promise.all(uploadPromises);
      alert("성공적으로 저장되었습니다!");
      
      if (onNavigate) onNavigate('diary');

    } catch (error) {
      console.error(error);
      alert("저장 실패: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans z-50">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        {/* [추가] 최상단 TopBar */}
        {/* <TopBar user={user} onNavigate={onNavigate} /> */}

        <div className="px-5 pt-4 pb-4 bg-white sticky top-0 z-[9999] flex items-center justify-between border-b border-gray-100 shadow-sm">
            <button 
                type="button"
                onClick={() => onNavigate && onNavigate('diary')} 
                className="p-4 -ml-4 text-black hover:bg-gray-100 rounded-full cursor-pointer active:bg-gray-200"
            >
                <span className="text-xl font-bold">〈</span>
            </button>
            <h1 className="text-lg font-bold text-black">{initialDiary ? "낚시 일지 수정" : "낚시 일지 등록"}</h1>
            <button 
                type="button"
                onClick={handleSave} 
                disabled={loading}
                className={`bg-indigo-50 text-indigo-600 px-4 py-2 rounded-full text-sm font-bold transition-all ${loading ? 'opacity-50' : 'active:scale-95'}`}
            >
              {loading ? '저장 중...' : '저장'}
            </button>
        </div>

        <div className="flex-1 overflow-y-auto no-scrollbar p-5 pb-32 bg-gray-50">
          {logs.map((log, index) => (
            <div key={log.id} className="bg-white rounded-[20px] p-5 mb-5 shadow-sm border border-gray-100 relative">
              
              <div className="flex justify-between items-center mb-4">
                <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500">
                  {index + 1}
                </div>
                {logs.length > 1 && (
                  <button onClick={() => removeLog(log.id)} className="text-xs font-bold text-red-500 bg-red-50 px-2 py-1 rounded-md">삭제</button>
                )}
              </div>

              <div className="flex items-center justify-between py-3 border-b border-gray-50">
                  <span className="text-[15px] font-bold text-gray-700">날짜</span>
                  <input 
                    type="datetime-local"
                    value={log.date}
                    onChange={(e) => updateLog(log.id, 'date', e.target.value)}
                    className="bg-blue-50 text-blue-600 text-sm font-bold px-3 py-1.5 rounded-lg outline-none"
                  />
              </div>

              <div className="py-3 border-b border-gray-50">
                <div className="flex justify-between items-center mb-2">
                    <span className="text-[15px] font-bold text-gray-700">어종 / 마릿수</span>
                </div>
                <div className="space-y-3">
                    {log.catches.map((catchItem) => (
                        <div key={catchItem.id} className="flex items-center justify-between bg-gray-50 p-2 rounded-xl">
                            <div className="flex gap-1">
                                {['갑오징어', '쭈꾸미'].map((fish) => (
                                    <button
                                        key={fish}
                                        onClick={() => updateCatchRow(log.id, catchItem.id, 'fishType', fish)}
                                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                                            catchItem.fishType === fish 
                                            ? 'bg-white border-blue-500 text-blue-600 shadow-sm' 
                                            : 'bg-transparent border-transparent text-gray-400'
                                        }`}
                                    >
                                        {fish}
                                    </button>
                                ))}
                            </div>
                            <div className="flex items-center gap-2">
                                <input 
                                    type="number"
                                    placeholder="0"
                                    value={catchItem.count}
                                    onChange={(e) => updateCatchRow(log.id, catchItem.id, 'count', e.target.value)}
                                    className="w-12 text-right font-bold text-gray-800 bg-transparent outline-none border-b border-gray-300 focus:border-blue-500"
                                />
                                <span className="text-xs text-gray-500">마리</span>
                                <button onClick={() => removeCatchRow(log.id, catchItem.id)} className="ml-1 text-gray-300 hover:text-red-500 px-1">✕</button>
                            </div>
                        </div>
                    ))}
                </div>
                <button onClick={() => addCatchRow(log.id)} className="mt-3 w-full py-2 text-xs font-bold text-blue-500 bg-blue-50 rounded-lg border border-dashed border-blue-200 hover:bg-blue-100 transition-colors">+ 어종 추가하기</button>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-gray-50">
                  <span className="text-[15px] font-bold text-gray-700">위치</span>
                  <button 
                    onClick={() => openPortModal(log.id)}
                    className={`flex-1 text-right text-sm ${log.location ? 'text-gray-900 font-medium' : 'text-gray-400'}`}
                  >
                    {log.location || "항구명 검색 (클릭)"} 🔍
                  </button>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-gray-50">
                  <span className="text-[15px] font-bold text-gray-700">선박</span>
                  <input 
                    type="text" 
                    placeholder="배 이름 입력 (선택)" 
                    value={log.boatName} 
                    onChange={(e) => updateLog(log.id, 'boatName', e.target.value)} 
                    className="text-right flex-1 ml-4 outline-none text-gray-800 text-sm bg-transparent" 
                  />
              </div>

              {/* [수정] 에기 선택: 선택된 에기를 색상 태그로 표시 */}
              <div className="py-3 border-b border-gray-50">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[15px] font-bold text-gray-700">에기</span>
                    <button 
                        type="button"
                        onClick={() => openEgiModal(log.id)}
                        className="text-xs font-bold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100 shadow-sm"
                    >
                        + 선택하기
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2 min-h-[30px] p-2 bg-gray-50 rounded-lg">
                    {log.selectedEgis.length === 0 ? (
                        <span className="text-xs text-gray-400">선택된 에기가 없습니다.</span>
                    ) : (
                        log.selectedEgis.map((egi) => {
                            const style = COLOR_STYLES[egi.color_name] || COLOR_STYLES['기타'];
                            return (
                                <span 
                                    key={egi.color_id} 
                                    className="text-xs font-bold px-2 py-1 rounded border flex items-center gap-1 shadow-sm"
                                    style={{
                                        background: style.bg,
                                        color: style.text,
                                        borderColor: style.border === 'transparent' ? 'transparent' : style.border
                                    }}
                                >
                                    {egi.color_name}
                                    <button 
                                        type="button"
                                        onClick={(e) => { e.stopPropagation(); setCurrentLogId(log.id); toggleEgiSelection(egi); }}
                                        className="hover:opacity-60 ml-1"
                                        style={{ color: style.text }}
                                    >✕</button>
                                </span>
                            );
                        })
                    )}
                  </div>
              </div>

              <div className="mt-4">
                  <span className="text-[15px] font-bold text-gray-700 block mb-2">메모</span>
                  <textarea placeholder="팁을 적어주세요." value={log.content} onChange={(e) => updateLog(log.id, 'content', e.target.value)} className="w-full h-20 bg-gray-50 rounded-xl p-3 text-sm outline-none resize-none text-gray-700" />
              </div>

              <div className="mt-4">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[15px] font-bold text-gray-700">사진 ({log.images.length})</span>
                    <label className="text-xs font-bold text-blue-600 cursor-pointer bg-blue-50 px-2 py-1 rounded hover:bg-blue-100">
                        + 추가
                        <input type="file" multiple accept="image/*" className="hidden" onChange={(e) => handleFileChange(e, log.id)} />
                    </label>
                  </div>
                  <div className="flex gap-2 overflow-x-auto no-scrollbar pb-2 min-h-[70px]">
                    {log.images.length === 0 && <span className="text-xs text-gray-300 py-4 pl-2">등록된 사진이 없습니다.</span>}
                    {log.images.map((imgObj, idx) => (
                        <div key={idx} className="relative w-16 h-16 flex-shrink-0">
                            <img 
                                src={imgObj.url} 
                                alt="preview" 
                                className="w-full h-full rounded-lg object-cover bg-gray-100 border border-gray-100" 
                            />
                            <button 
                                onClick={() => handleRemoveImage(log.id, idx)}
                                className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold shadow-md hover:bg-red-600 transition-colors"
                            >
                                ✕
                            </button>
                        </div>
                    ))}
                  </div>
              </div>
            </div>
          ))}

          <button onClick={addLog} className="w-full py-4 border-2 border-dashed border-gray-300 rounded-2xl text-gray-400 font-bold flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors mb-10">
            <span className="text-xl">+</span> 일지 추가하기
          </button>
        </div>

        {/* 에기 선택 모달 */}
        {isEgiModalOpen && (
            <div className="absolute inset-0 z-[10000] bg-black/60 flex items-end justify-center backdrop-blur-sm">
                <div className="absolute inset-0" onClick={() => setIsEgiModalOpen(false)}></div>
                <div className="relative w-full bg-white rounded-t-[30px] p-6 h-[500px] flex flex-col animate-in slide-in-from-bottom duration-300 shadow-2xl">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-gray-800">에기 색상 선택</h3>
                        <button type="button" onClick={() => setIsEgiModalOpen(false)} className="text-gray-500 font-bold p-2 bg-gray-100 rounded-lg">닫기</button>
                    </div>
                    {/* [수정] 모달 내 버튼들도 색상 스타일 적용 */}
                    <div className="flex-1 overflow-y-auto no-scrollbar grid grid-cols-3 gap-3 pb-4 content-start">
                        {egiColors.map((color) => {
                            const currentLog = logs.find(l => l.id === currentLogId);
                            const isSelected = currentLog?.selectedEgis.some(e => e.color_id === color.color_id);
                            const style = COLOR_STYLES[color.color_name] || COLOR_STYLES['기타'];

                            return (
                                <button
                                    key={color.color_id}
                                    type="button"
                                    onClick={() => { setCurrentLogId(currentLogId); toggleEgiSelection(color); }}
                                    style={{
                                        background: style.bg,
                                        color: style.text,
                                        border: `1px solid ${style.border}`,
                                        boxShadow: isSelected ? '0 0 0 2px #ffffff, 0 0 0 4px #000000' : 'none',
                                        opacity: isSelected ? 1 : 0.7
                                    }}
                                    className={`py-3 px-2 rounded-xl text-sm font-bold transition-all active:scale-95`}
                                >
                                    {color.color_name}
                                </button>
                            );
                        })}
                    </div>
                    <button type="button" onClick={() => setIsEgiModalOpen(false)} className="w-full py-4 bg-indigo-600 text-white font-bold rounded-2xl mt-2">선택 완료</button>
                </div>
            </div>
        )}

        {isPortModalOpen && (
            <div className="absolute inset-0 z-[10000] bg-black/60 flex items-end justify-center backdrop-blur-sm">
                <div className="absolute inset-0" onClick={() => setIsPortModalOpen(false)}></div>
                <div className="relative w-full bg-white rounded-t-[30px] p-6 h-[600px] flex flex-col animate-in slide-in-from-bottom duration-300 shadow-2xl">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold text-gray-800">항구 검색</h3>
                        <button type="button" onClick={() => setIsPortModalOpen(false)} className="text-gray-500 font-bold p-2 bg-gray-100 rounded-lg">닫기</button>
                    </div>
                    <div className="flex gap-2 mb-4">
                        <input 
                            type="text" 
                            className="flex-1 bg-gray-100 rounded-xl px-4 py-3 text-sm outline-none border border-transparent focus:border-indigo-500 transition-all"
                            placeholder="항구 이름 입력 (예: 덕포)"
                            value={portSearchQuery}
                            onChange={(e) => setPortSearchQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && searchPorts()}
                        />
                        <button onClick={searchPorts} className="bg-indigo-600 text-white px-4 py-2 rounded-xl font-bold text-sm">검색</button>
                    </div>
                    <div className="flex-1 overflow-y-auto no-scrollbar">
                        {isSearchingPort ? (
                            <div className="text-center py-10 text-gray-400">검색 중...</div>
                        ) : portSearchResults.length > 0 ? (
                            <div className="space-y-3">
                                {portSearchResults.map((port, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => selectPort(port)}
                                        className="w-full text-left p-4 bg-gray-50 rounded-xl border border-gray-100 hover:bg-indigo-50 hover:border-indigo-200 transition-all"
                                    >
                                        <div className="font-bold text-gray-800 text-sm">{port.port_name}</div>
                                        <div className="text-xs text-gray-500 mt-1">{port.address}</div>
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-10 text-gray-400 text-sm">
                                검색 결과가 없습니다.<br/>정확한 항구명을 입력해보세요.
                            </div>
                        )}
                    </div>
                </div>
            </div>
        )}

      </div>
    </div>
  );
};

export default DiaryWriteScreen;