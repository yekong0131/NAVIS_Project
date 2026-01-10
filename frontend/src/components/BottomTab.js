// src/components/BottomTab.js
import React from 'react';

function BottomTab({ activeTab, onNavigate, onCameraClick }) {
  return (
    <div className="absolute bottom-0 left-0 w-full bg-white/95 border-t border-gray-100 flex justify-around items-end pb-8 h-[95px] z-20 text-black backdrop-blur-sm">
      
      {/* 1. 홈 탭 */}
      <button 
        onClick={() => onNavigate('home')} 
        className={`flex flex-col items-center transition-colors ${activeTab === 'home' ? 'text-gray-900' : 'text-gray-400 hover:text-gray-600'}`}
      >
        <span className="text-2xl mb-1">🏠</span>
        <span className={`text-[10px] ${activeTab === 'home' ? 'font-bold' : ''}`}>홈</span>
      </button>
      
      {/* 2. 선박예약 탭 */}
      <button 
        onClick={() => onNavigate('boat-search')} 
        className={`flex flex-col items-center transition-colors ${activeTab === 'boat-search' ? 'text-blue-600' : 'text-gray-400 hover:text-blue-500'}`}
      >
        <span className="text-2xl mb-1">🚢</span>
        <span className={`text-[10px] ${activeTab === 'boat-search' ? 'font-bold' : ''}`}>선박예약</span>
      </button>
      
      {/* 3. 카메라 버튼 */}
      <div className="relative -mt-12">
        <button 
          onClick={onCameraClick} 
          className="w-16 h-16 bg-white rounded-full border-[4px] border-blue-500 flex items-center justify-center shadow-xl active:scale-90 transition-transform"
        >
          <span className="text-3xl">📷</span>
        </button>
      </div>
      
      {/* 4. 낚시일지 탭 */}
      <button 
        onClick={() => onNavigate('diary')} 
        className={`flex flex-col items-center transition-colors ${activeTab === 'diary' ? 'text-yellow-500' : 'text-gray-400 hover:text-yellow-500'}`}
      >
        <span className="text-2xl mb-1">📒</span>
        <span className={`text-[10px] ${activeTab === 'diary' ? 'font-bold' : ''}`}>낚시일지</span>
      </button>
      
      {/* 5. 내정보 탭 (수정됨) */}
      <button 
        // [수정] 이동할 화면 이름을 'profile'로 변경 (App.js와 일치시킴)
        onClick={() => onNavigate('profile')} 
        className={`flex flex-col items-center transition-colors ${activeTab === 'profile' ? 'text-gray-900' : 'text-gray-400'}`}
      >
        <span className="text-2xl mb-1">👤</span>
        <span className={`text-[10px] ${activeTab === 'profile' ? 'font-bold' : ''}`}>내정보</span>
      </button>

    </div>
  );
}

export default BottomTab;