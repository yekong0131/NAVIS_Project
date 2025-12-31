// src/components/TopBar.js
import React from 'react';
// 이미지 경로가 다를 수 있으니 프로젝트에 맞게 확인해주세요 (ex: ../assets/...)
import wangpandaImg from "../assets/wangpanda2.png"; 
import yongwangLogoImg from "../assets/logo_yongwang.png"; 

function TopBar({ user, onNavigate }) {
  return (
    <div className="px-5 pt-2 sticky top-0 bg-white z-20 pb-2 shadow-sm">
      
      {/* 1. 상태바 */}
      <div className="flex justify-between items-center text-[12px] font-bold mb-3 text-black">
        <span>9:41</span>
        <div className="flex gap-1">📶🔋</div>
      </div>

      {/* 2. 앱 타이틀 & 로그인/회원정보 영역 */}
      <div className="relative flex justify-between items-center text-black mb-2 h-8">
        
        {/* 왼쪽: 로고 */}
        <div className="flex items-center gap-2 z-10">
          <div className="w-8 h-8 flex items-center justify-start">
            <img 
              src={wangpandaImg} 
              alt="Panda Logo" 
              className="w-full h-full object-contain drop-shadow-sm" 
            />
          </div>
        </div>

        {/* 중앙: 타이틀 */}
        <div className="absolute left-1/2 transform -translate-x-1/2 h-full flex items-center justify-center>">
          <img 
            src={yongwangLogoImg} 
            alt="YongWang Logo" 
            className="h-6 object-contain" 
          />
        </div>

        {/* 오른쪽: 로그인 상태에 따른 버튼 표시 */}
        <div className="flex items-center justify-end z-10 min-w-[60px]">
          {user ? (
            <div 
                className="flex items-center gap-2 cursor-pointer active:opacity-70 transition-opacity"
                // [수정] 클릭 시 '내 정보(profile)' 화면으로 이동 (바로 수정화면 X)
                onClick={() => onNavigate('profile')} 
            >
              <span className="text-xs font-bold text-gray-700 hidden sm:block">
                {user.nickname || user.username} 님
              </span>
              <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center overflow-hidden shadow-sm">
                {user.profile_image ? (
                  <img src={user.profile_image} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <span className="text-sm">👤</span>
                )}
              </div>
            </div>
          ) : (
            <button 
              onClick={() => onNavigate('login')}
              className="bg-indigo-500 hover:bg-indigo-600 text-white text-[11px] font-bold px-3 py-1.5 rounded-full shadow-sm active:scale-95 transition-transform"
            >
              로그인
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default TopBar;