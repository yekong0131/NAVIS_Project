import React, { useState } from "react";
import TopBar from "../components/TopBar";
import BottomTab from "../components/BottomTab";
// 이미지 경로는 프로젝트 구조에 맞춰 수정해주세요.
import defaultProfileImg from "../assets/login_panda.png"; 

function Myprofile({ user, onNavigate, onLogout, goToLikeList, goToFishingDiary }) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const activityMenu = [
    { id: 1, title: "❤️ 좋아요 선박 리스트", icon: "🚢" },
    { id: 2, title: "☁️ 낚시일지 드라이브", icon: "📂" },
  ];

  const settingMenu = [
    { id: 1, title: "알림 설정", icon: "🔔" },
    { id: 2, title: "공지사항", icon: "📢" },
    { id: 3, title: "고객센터", icon: "🎧" },
  ];

  const handleMenuClick = (id) => {
    if (id === 1) {
      if (goToLikeList) goToLikeList();
      else alert("기능 연결 확인 필요: 좋아요 리스트");
    }
    else if (id === 2) {
      if (goToFishingDiary) goToFishingDiary();
      else alert("기능 연결 확인 필요: 낚시일지");
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        
        {/* 1. TopBar 추가 */}
        <TopBar user={user} onNavigate={onNavigate} />

        {/* 2. 메인 컨텐츠 영역 (기존 내용 유지하되 스타일 조정) */}
        <div className="flex-1 overflow-y-auto no-scrollbar px-5 py-6 space-y-6 pb-32 bg-[#F8F9FA]">
          
          {/* (기존의 상단 헤더/X버튼 제거됨) */}

          {/* 프로필 카드 */}
          <div className="bg-white rounded-[24px] p-6 shadow-sm flex items-center gap-5 border border-gray-50">
            <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-pink-100 flex-shrink-0 bg-gray-100">
              <img 
                src={user?.profile_image || defaultProfileImg} 
                alt="Profile" 
                className="w-full h-full object-cover" 
              />
            </div>
            <div className="text-left">
              <h3 className="text-[20px] font-black text-gray-900">
                  {user?.nickname || "게스트"}
              </h3>
              <p className="text-[13px] text-blue-500 font-bold mt-1">
                  {user?.email || "로그인이 필요합니다"}
              </p>
              <button 
                onClick={() => onNavigate('password-confirm')} // 정보 수정 페이지로 이동
                className="text-[11px] text-gray-400 underline mt-2"
              >
                내 정보 수정
              </button>
            </div>
          </div>

          {/* 활동 메뉴 리스트 */}
          <div className="bg-white rounded-[24px] overflow-hidden shadow-sm border border-gray-50 text-left">
            {activityMenu.map((item, index) => (
              <div 
                key={item.id} 
                onClick={() => handleMenuClick(item.id)}
                className={`p-5 flex justify-between items-center cursor-pointer active:bg-gray-50 transition-colors ${index !== activityMenu.length - 1 ? 'border-b border-gray-50' : ''}`}
              >
                <div className="flex items-center gap-3">
                    <span>{item.icon}</span>
                    <span className="font-bold text-[15px] text-gray-700">{item.title}</span>
                </div>
                <span className="text-gray-300">〉</span>
              </div>
            ))}
          </div>

          {/* 설정 메뉴 및 로그아웃 */}
          <div className="bg-white rounded-[24px] overflow-hidden shadow-sm border border-gray-100 text-left">
            {settingMenu.map((item, index) => (
              <div key={item.id} className={`p-5 flex justify-between items-center cursor-pointer active:bg-gray-50 ${index !== settingMenu.length - 1 ? 'border-b border-gray-50' : ''}`}>
                <div className="flex items-center gap-3">
                    <span>{item.icon}</span>
                    <span className="font-bold text-[15px] text-gray-700">{item.title}</span>
                </div>
                <span className="text-gray-300">〉</span>
              </div>
            ))}
            <div onClick={onLogout} className="p-5 flex justify-between items-center bg-red-50 cursor-pointer active:bg-red-100">
              <span className="font-bold text-[15px] text-red-500">로그아웃</span>
              <span className="text-red-200 text-lg font-bold">〉</span>
            </div>
          </div>
        </div>

        {/* 3. BottomTab 추가 */}
        <BottomTab 
          activeTab="profile" 
          onNavigate={onNavigate} 
          onCameraClick={() => setIsModalOpen(true)}
        />

        {/* 카메라 모달 (BottomTab 작동용) */}
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

export default Myprofile;