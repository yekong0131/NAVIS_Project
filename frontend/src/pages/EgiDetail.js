// src/pages/EgiDetail.js
import React, { useState } from 'react';
import TopBar from '../components/TopBar'; // TopBar import

const COLOR_STYLES = {
    '빨강': { bg: '#FF4D4D' },
    '주황': { bg: '#FF9F43' },
    '노랑': { bg: '#FFD32A' },
    '초록': { bg: '#2ECC71' },
    '파랑': { bg: '#3498DB' },
    '보라': { bg: '#9B59B6' },
    '핑크': { bg: '#EF5777' },
    '갈색': { bg: '#8D6E63' },
    '무지개': { bg: 'linear-gradient(45deg, #FF0000, #FF7F00, #FFFF00, #00FF00, #0000FF, #4B0082, #9400D3)' },
    '기타': { bg: '#95A5A6' },
};

// [추가] 인앱 브라우저 모달 컴포넌트
const WebViewModal = ({ url, onClose }) => {
  if (!url) return null;
  return (
    <div className="absolute inset-0 z-[60] flex flex-col bg-white animate-in slide-in-from-bottom duration-300">
      <div className="flex justify-between items-center px-4 py-3 border-b border-gray-200 bg-white shadow-sm shrink-0">
        <span className="font-bold text-gray-800 text-sm truncate flex-1 pr-4">{url}</span>
        <button onClick={onClose} className="px-3 py-1 bg-gray-100 text-gray-600 rounded-lg text-sm font-bold active:bg-gray-200 shrink-0">닫기 ✕</button>
      </div>
      <div className="flex-1 w-full h-full bg-gray-50 relative">
        <iframe src={url} title="Purchase WebView" className="w-full h-full border-0" />
      </div>
    </div>
  );
};

const EgiDetail = ({ egi, onBack, user, onNavigate }) => {
    const [webViewUrl, setWebViewUrl] = useState(null); // [추가] 웹뷰 URL 상태

    if (!egi) return null;

    const dotStyle = egi && egi.color_name ? (COLOR_STYLES[egi.color_name] || COLOR_STYLES['기타']) : { bg: '#DDD' };

    const handleBuyClick = () => {
        if (egi.purchase_url) {
            // [수정] 모달로 URL 설정 (인앱 브라우저 열기)
            setWebViewUrl(egi.purchase_url);
        } else {
            alert("구매 링크가 제공되지 않는 상품입니다.");
        }
    };

    return (
        <div className="fixed inset-0 bg-slate-100 flex justify-center font-sans z-50">
            <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col shadow-2xl overflow-hidden">
                
                {/* [추가] 최상단 TopBar */}
                <TopBar user={user} onNavigate={onNavigate} />

                {/* 헤더 */}
                <div className="h-[60px] flex items-center px-4 border-b border-gray-100 bg-white z-10">
                    <button onClick={onBack} className="text-2xl mr-4 text-gray-700 font-bold p-1">←</button>
                    <h1 className="font-bold text-lg text-gray-800">상품 상세</h1>
                </div>

                <div className="flex-1 overflow-y-auto pb-24 no-scrollbar bg-white">
                    {/* 이미지 영역 */}
                    <div className="w-full aspect-square bg-gray-50 flex items-center justify-center p-10 relative">
                        <img src={egi.image_url} alt={egi.name} className="w-full h-full object-contain drop-shadow-xl" />
                        <div className="absolute top-4 right-4 bg-white/80 backdrop-blur px-3 py-1 rounded-full text-xs font-bold text-gray-500 border border-gray-100">
                            {egi.brand}
                        </div>
                    </div>

                    {/* 정보 영역 */}
                    <div className="px-6 py-8">
                        <h2 className="text-xl font-bold text-gray-900 leading-snug mb-2">
                            {egi.name}
                        </h2>
                        <p className="text-sm text-gray-500 mb-8">{egi.brand} 정품</p>

                        <div className="space-y-4 border-t border-gray-100 pt-6">
                            <div className="flex justify-between items-center py-2">
                                <span className="text-gray-500 text-sm">색상 타입</span>
                                <div className="flex items-center gap-2">
                                    <span 
                                        className="w-3 h-3 rounded-full inline-block shadow-sm ring-1 ring-gray-100"
                                        style={{ background: dotStyle.bg }}
                                    ></span>
                                </div>
                            </div>
                            <div className="flex justify-between items-center py-2 border-t border-gray-50">
                                <span className="text-gray-500 text-sm">사이즈(호수)</span>
                                <span className="font-bold text-gray-800">{egi.size || "Free"}</span>
                            </div>
                             <div className="flex justify-between items-center py-2 border-t border-gray-50">
                                <span className="text-gray-500 text-sm">특징</span>
                                <span className="font-medium text-gray-800 text-sm text-right max-w-[200px] leading-relaxed">
                                    {egi.description || "상세 설명이 없습니다."}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 하단 구매 버튼 */}
                <div className="absolute bottom-0 left-0 right-0 p-5 bg-white border-t border-gray-100 shadow-[0_-4px_10px_rgba(0,0,0,0.05)] z-20">
                    <button 
                        onClick={handleBuyClick}
                        className={`w-full font-bold text-lg py-4 rounded-2xl shadow-lg active:scale-98 transition-transform flex items-center justify-center gap-2 ${
                            egi.purchase_url 
                            ? "bg-blue-600 text-white hover:bg-blue-700" 
                            : "bg-gray-200 text-gray-400 cursor-not-allowed"
                        }`}
                        disabled={!egi.purchase_url}
                    >
                       {egi.purchase_url ? (
                           <>
                             <span>구매하러 가기</span>
                             <span>🛍️</span>
                           </>
                       ) : "구매 링크 준비중"}
                    </button>
                </div>

                {/* [추가] 구매 링크 웹뷰 모달 */}
                {webViewUrl && (
                    <WebViewModal url={webViewUrl} onClose={() => setWebViewUrl(null)} />
                )}
            </div>
        </div>
    );
};

export default EgiDetail;