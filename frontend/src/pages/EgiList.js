// src/pages/EgiList.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import TopBar from '../components/TopBar';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const COLOR_STYLES = {
    'All': { bg: '#F3F4F6', text: '#4B5563', border: '#E5E7EB' },
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

const EgiList = ({ onNavigate, onBack, user }) => {
    const [egis, setEgis] = useState([]);
    const [colors, setColors] = useState([]);
    const [selectedColor, setSelectedColor] = useState('All');
    const [isLoading, setIsLoading] = useState(false);

    // 1. 색상 목록 불러오기
    useEffect(() => {
        axios.get(`${API_URL}/egi/colors/`)
            .then(res => {
                setColors([{ color_name: 'All' }, ...res.data]);
            })
            .catch(err => console.error("색상 로드 실패:", err));
    }, []);

    // 2. 에기 목록 불러오기
    useEffect(() => {
        const fetchEgis = async () => {
            setIsLoading(true);
            try {
                let url = `${API_URL}/egi/list/`;
                if (selectedColor !== 'All') {
                    url += `?color=${encodeURIComponent(selectedColor)}`;
                }
                const res = await axios.get(url);
                setEgis(res.data);
            } catch (err) {
                console.error("에기 목록 로드 실패:", err);
            } finally {
                setIsLoading(false);
            }
        };
        fetchEgis();
    }, [selectedColor]);

    return (
        <div className="fixed inset-0 bg-slate-100 flex justify-center font-sans">
            <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col shadow-2xl overflow-hidden">
             
                <TopBar user={user} onNavigate={onNavigate} />

                <div className="bg-white px-4 py-3 flex items-center border-b border-gray-100 z-10">
                    <button onClick={onBack} className="text-2xl mr-4 text-gray-700 font-bold p-1">〈</button>
                    <h1 className="font-bold text-lg text-gray-900">에기 도감</h1>
                </div>

                <div className="bg-white py-3 px-4 border-b border-gray-100 overflow-x-auto whitespace-nowrap no-scrollbar z-10">
                    {colors.map((c, idx) => {
                        const isSelected = selectedColor === c.color_name;
                        const style = COLOR_STYLES[c.color_name] || COLOR_STYLES['기타'];

                        return (
                            <button
                                key={idx}
                                onClick={() => setSelectedColor(c.color_name)}
                                style={{
                                    background: style.bg,
                                    color: style.text,
                                    border: `1px solid ${style.border}`,
                                    boxShadow: isSelected ? '0 0 0 2px #ffffff, 0 0 0 4px #000000' : 'none',
                                    opacity: (selectedColor !== 'All' && !isSelected) ? 0.5 : 1
                                }}
                                className={`px-4 py-2 rounded-full text-[13px] font-bold mr-3 transition-all active:scale-95 mb-1`}
                            >
                                {c.color_name === 'All' ? '전체' : c.color_name}
                            </button>
                        );
                    })}
                </div>

                <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
                    {isLoading ? (
                         <div className="flex justify-center items-center h-40 text-gray-400 text-sm">로딩 중...</div>
                    ) : egis.length > 0 ? (
                        <div className="grid grid-cols-2 gap-4 pb-20">
                            {egis.map((egi) => {
                                const tagStyle = COLOR_STYLES[egi.color_name] || COLOR_STYLES['기타'];
                                
                                return (
                                    <div 
                                        key={egi.egi_id} 
                                        onClick={() => onNavigate('egi-detail', { ...egi, fromPage: 'egi-list' })}
                                        className="bg-white rounded-2xl p-3 shadow-sm border border-gray-100 cursor-pointer active:scale-95 transition-transform"
                                    >
                                        <div className="w-full aspect-square bg-white rounded-xl mb-3 overflow-hidden flex items-center justify-center border border-gray-50 relative group">
                                            <img 
                                                src={egi.image_url} 
                                                alt={egi.name} 
                                                className="w-full h-full object-contain p-2 group-hover:scale-110 transition-transform duration-300" 
                                            />
                                            <div className="absolute top-2 left-2 bg-gray-900/5 text-gray-500 text-[10px] px-2 py-0.5 rounded font-bold">
                                                {egi.brand}
                                            </div>
                                        </div>
                                        
                                        {/* [수정] 3줄 표시 및 높이 조정 */}
                                        <h3 className="font-bold text-gray-800 text-[14px] line-clamp-3 h-[54px] leading-tight">
                                            {egi.name}
                                        </h3>
                                        
                                        <div className="flex justify-between items-center mt-2">
                                            <span 
                                                className="text-[11px] px-2 py-1 rounded font-bold border"
                                                style={{
                                                    background: tagStyle.bg,
                                                    color: tagStyle.text,
                                                    borderColor: tagStyle.border === 'transparent' ? 'transparent' : tagStyle.border
                                                }}
                                            >
                                                {egi.color_name || "정보 없음"}
                                            </span>
                                            <span className="text-[11px] text-gray-400">
                                                {egi.size ? `${egi.size}호` : ""}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400">
                            <span className="text-4xl mb-2">🎣</span>
                            <p className="text-sm">해당하는 에기가 없습니다.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default EgiList;