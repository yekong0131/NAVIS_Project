import React, { useState } from "react"; 
import axios from "axios"; 
import pandaLoginImg from "../assets/login_panda.png"; 
import kakaoImg from "../assets/kakao.jpg";
import naverImg from "../assets/naver.jpg";
import googleImg from "../assets/google.jpg";
import TopBar from '../components/TopBar';

function Login({ onLogin, onNavigate, user }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  const handleLoginClick = async () => {
    if (!username || !password) {
        alert("아이디와 비밀번호를 입력해주세요.");
        return;
    }

    try {
        const response = await axios.post(`${API_URL}/auth/login/`, {
            username: username,
            password: password
        });
        
        if (response.status === 200) {
            const { token, user } = response.data;
            localStorage.setItem('authToken', token); 
            console.log("로그인 성공:", user);
            onLogin(user); 
        }
    } catch (err) {
        console.error("로그인 에러:", err);
        alert("로그인 실패: 아이디와 비밀번호를 확인하세요.");
    }
  };

  // [추가] 엔터 키 감지 핸들러
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleLoginClick();
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col shadow-2xl border-x border-gray-100">
        {/* [추가] 최상단 TopBar */}
        {/* <TopBar user={user} onNavigate={onNavigate} /> */}

        {/* 1. 상단 네비게이션 */}
        <div className="flex justify-between items-center px-5 py-4">
            <button 
                onClick={() => onNavigate('home')} 
                className="text-2xl text-gray-500 p-1 -ml-2"
            >
                ✕
            </button>
            <span className="font-bold text-xl">로그인</span>
            <div className="w-8"></div>
        </div>

        {/* 2. 콘텐츠 영역 */}
        <div className="flex-1 overflow-y-auto no-scrollbar px-6 pt-4 text-center text-black">
          
          <div className="flex justify-center mb-6">
            <img 
              src={pandaLoginImg} 
              alt="Panda" 
              className="w-64 h-64 object-contain" 
            />
          </div>

          {/* 로그인 입력 폼 */}
          <div className="flex flex-col gap-4 px-2 mb-8">
            <input 
              type="text"
              placeholder="아이디"
              value={username} 
              onChange={(e) => setUsername(e.target.value)}
              onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
              className="w-full py-4 bg-white text-[#7e96ff] border border-[#7e96ff] placeholder-[#7e96ff]/70 rounded-2xl font-bold text-[16px] text-left px-8 outline-none shadow-sm transition-transform active:scale-95"
            />

            <input 
              type="password"
              placeholder="비밀번호"
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
              className="w-full py-4 bg-white text-[#7e96ff] border border-[#7e96ff] placeholder-[#7e96ff]/70 rounded-2xl font-bold text-[16px] text-left px-8 outline-none shadow-sm transition-transform active:scale-95"
            />

            <button 
              onClick={handleLoginClick} 
              className="w-full py-4 bg-[#7e96ff] text-white rounded-2xl font-bold text-[18px] mt-2 shadow-sm active:scale-95 transition-transform flex items-center justify-center"
            >
              로그인
            </button>

            <div className="flex justify-center items-center gap-3 mt-4 text-[13px] text-gray-400 font-medium">
              <span className="cursor-pointer hover:text-gray-600">아이디 찾기</span>
              <span className="text-gray-200">|</span>
              <span className="cursor-pointer hover:text-gray-600">비밀번호 찾기</span>
              <span className="text-gray-200">|</span>
              <span 
                onClick={() => onNavigate('signup')} 
                className="cursor-pointer hover:text-gray-600 font-bold text-gray-400"
              >
                회원 가입
              </span>
            </div>
          </div>

          {/* 소셜 로그인 구분선 */}
          <div className="flex items-center gap-4 px-2 my-10">
            <div className="flex-1 h-[1px] bg-gray-300"></div>
            <span className="text-gray-500 text-[12px] font-medium">SNS 계정으로 간편 로그인</span>
            <div className="flex-1 h-[1px] bg-gray-300"></div>
          </div>

          {/* 소셜 로그인 버튼들 */}
          <div className="flex flex-col gap-6 pb-12">
            <button className="w-full py-3 bg-[#fee500] rounded-2xl font-bold flex items-center px-5 active:scale-95 transition-transform shadow-sm relative">
              <img src={kakaoImg} alt="Kakao" className="w-8 h-8 rounded-lg object-contain" />
              <span className="flex-1 text-[15px] text-black text-center pr-8">Kakao 계정으로 로그인</span>
            </button>

            <button className="w-full py-3 bg-[#03c75a] text-white rounded-2xl font-bold flex items-center px-5 active:scale-95 transition-transform shadow-sm relative">
              <img src={naverImg} alt="Naver" className="w-8 h-8 rounded-lg object-contain" />
              <span className="flex-1 text-[15px] text-center pr-8">Naver 계정으로 로그인</span>
            </button>

            <button className="w-full py-3 bg-white border border-gray-200 rounded-2xl font-bold flex items-center px-5 active:scale-95 transition-transform shadow-sm relative">
              <img src={googleImg} alt="Google" className="w-8 h-8 rounded-lg object-contain" />
              <span className="flex-1 text-[15px] text-black text-center pr-8">Google 계정으로 로그인</span>
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Login;