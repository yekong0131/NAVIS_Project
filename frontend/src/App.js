import React, { useState } from "react";
import Login from "./pages/Login";
import Home from "./pages/Home";
import FishingDiaryScreen from "./pages/FishingDiaryScreen";
import AnalysisModal from "./components/AnalysisModal";
import ResultModal from "./components/ResultModal";
import SuccessWater from "./components/Success_water";
import DiaryWriteScreen from "./pages/DiaryWriteScreen";
import VoiceRecordScreen from "./pages/VoiceRecordScreen";
import BoatSearchScreen from "./pages/BoatSearchScreen";
import BoatDetailScreen from "./pages/BoatDetailScreen";
import MyLikedBoatsScreen from "./pages/MyLikedBoatsScreen"; // [추가] 찜 목록 화면
import Signup from "./pages/Signup";
import UserProfileEditScreen from "./pages/UserProfileEditScreen";
import PasswordConfirmScreen from "./pages/PasswordConfirmScreen"
import DiarySummary from "./pages/DiarySummary"
import Myprofile from "./pages/Myprofile"; 

function App() {
  const [screen, setScreen] = useState("login"); // login, home, diary, write...
  const [status, setStatus] = useState("idle");  // idle, loading, success, result
  const [progress, setProgress] = useState(0);

  const [user, setUser] = useState(null);
 
  // 데이터 전달용 상태
  const [selectedDiary, setSelectedDiary] = useState(null);
  const [selectedBoat, setSelectedBoat] = useState(null);
  
  const [sourcePage, setSourcePage] = useState("home");

  const handleLoginSuccess = (userData) => {
    console.log("로그인 성공:", userData);
    // userData 예시: { username: "test", nickname: "강태공", email: "..." }
    setUser(userData); 
    setScreen("home");
  };

  const handleUserUpdate = (updatedUser) => {
    console.log("유저 정보 갱신:", updatedUser);
    setUser(updatedUser);
  };
  
  // 📸 촬영 후 실행될 분석 함수 (시뮬레이션)
  const handleCapture = (isSea) => {
    setStatus("loading");
    setProgress(0);

    let p = 0;
    const interval = setInterval(() => {
      p += 5;
      setProgress(p);

      if (p >= 100) {
        clearInterval(interval);
        setTimeout(() => {
          if (isSea) {
            setStatus("success");
          } else {
            setStatus("result");
          }
        }, 500);
      }
    }, 30);
  };

  // 🧭 페이지 네비게이션 함수
  const handleNavigate = (page, data = null) => {
    console.log("Navigating to:", page, data); 
    
    // [1] 로그인이 필요한 페이지 목록 정의
    const authRequiredPages = [
        'diary',           // 낚시 일지
        'diary_summary',   // 낚시 일지 요약
        'profile',         // 내 정보
        'profile-edit',    // 회원 정보 수정
        'my-likes',        // 찜 목록
        'write',           // 일지 작성
        'voice-record'     // 음성 녹음
    ];

    // [2] 로그인 안 된 상태에서 접근 시 차단
    if (authRequiredPages.includes(page) && !user) {
        alert("로그인 후 이용해 주세요.");
        setScreen("login");
        return; // 이동 중단
    }

    // 정상 이동 로직
    if (data && data.fromPage) {
        setSourcePage(data.fromPage);
    }

    if (page === 'write') {
        setSelectedDiary(data ? data : null);
    }

    if (page === 'boat-detail' && data) {
        setSelectedBoat(data);
    }

    setScreen(page);
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-[360px] h-[740px] bg-white rounded-[40px] relative border-[8px] border-gray-800 overflow-hidden">
        
        {/* 1. 로그인 화면 */}
        {screen === "login" && (
          <Login 
            onLogin={(user) => handleLoginSuccess(user)} // [수정] user 정보 받도록 변경 필요 (Login.js 수정 필요, 아래 참조)
            onNavigate={handleNavigate} 
          />
        )}
        
        {screen === "signup" && (
          <Signup onNavigate={handleNavigate} />
        )}
        
        {screen === "home" && (
          <Home 
            user={user} // [중요] 닉네임이 포함된 user 정보 전달
            onCapture={handleCapture} 
            onNavigate={handleNavigate} 
          />
        )}
        
        {/* 3. 낚시 일지 목록 */}
        {screen === "diary" && (
          <FishingDiaryScreen 
            user={user} 
            onNavigate={handleNavigate} />
        )}
        
        {/* 4. 음성 녹음 화면 */}
        {screen === "voice-record" && (
          <VoiceRecordScreen 
            user={user}
            onNavigate={handleNavigate} />
        )}

        {/* 5. 일지 작성/수정 화면 */}
        {screen === "write" && (
          <DiaryWriteScreen 
            user={user}
            onNavigate={handleNavigate} 
            initialDiary={selectedDiary} // 수정할 데이터 전달
          />
        )}

        {/* 6. 선박 조회 화면 */}
        {screen === "boat-search" && (
          <BoatSearchScreen 
            user={user}
            onNavigate={handleNavigate} />
        )}

        {/* 7. 선박 상세 화면 */}
        {screen === "boat-detail" && (
          <BoatDetailScreen 
            user={user}
            boat={selectedBoat} 
            onNavigate={handleNavigate} 
          />
        )}

        {/* 8. [추가] 내가 찜한 선박 화면 */}
        {screen === "my-likes" && (
            <MyLikedBoatsScreen 
              user={user}
              onNavigate={handleNavigate}
              fromPage={sourcePage} // [추가] 저장해둔 이전 페이지 정보를 전달
            />
        )}

        {/* [추가] 비밀번호 확인 화면 */}
        {screen === "password-confirm" && (
          <PasswordConfirmScreen onNavigate={handleNavigate} />
        )}

        {/* 회원 정보 수정 화면 */}
        {screen === "profile-edit" && (
          <UserProfileEditScreen 
            user={user}
            onNavigate={handleNavigate}
            onUserUpdate={handleUserUpdate} 
          />
        )}

        {/* [수정] 프로필 화면 연결 */}
        {screen === "profile" && (
          <Myprofile 
            user={user} // 유저 정보 전달 (프로필 사진 표시용)
            onNavigate={handleNavigate}
            onLogout={() => {
                // [3] 로그아웃: 토큰 삭제 + 유저 상태 초기화 + 로그인화면 이동
                localStorage.removeItem('authToken');
                setUser(null);
                setScreen("login");
            }}
            goToHome={() => setScreen("home")} 
            
            // [중요] '좋아요 선박 리스트' 클릭 시 -> 'my-likes' 화면으로
            goToLikeList={() => handleNavigate("my-likes", { fromPage: 'profile' })}

            // [중요] '낚시일지 N드라이브' 클릭 시 -> 'diary_summary' 화면으로
            goToFishingDiary={() => setScreen("diary_summary")} 
          />
        )}

        {screen === "diary_summary" && (
              <DiarySummary onBack={() => setScreen("profile")} />
        )}

        {/* === 모달(팝업) 컴포넌트 === */}
        {status === "loading" && <AnalysisModal progress={progress} />}
        {status === "success" && <SuccessWater onClose={() => setStatus("idle")} />}
        {status === "result" && <ResultModal onRetry={() => setStatus("idle")} />}

      </div>
    </div>
  );
}

export default App;