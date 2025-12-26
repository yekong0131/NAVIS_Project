import React, { useState } from "react";
import axios from "axios";
import pandaImg from "../assets/login_panda.png"; // 기존 이미지 재사용

function PasswordConfirmScreen({ onNavigate }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  
  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  const handleVerify = async () => {
    if (!password) return;

    try {
        const token = localStorage.getItem('authToken');
        await axios.post(
            `${API_URL}/auth/verify-password/`, 
            { password },
            { headers: { Authorization: `Token ${token}` } }
        );
        // 성공 시 회원정보 수정 페이지로 이동
        onNavigate('profile-edit');
    } catch (err) {
        console.error(err);
        setError("비밀번호가 일치하지 않습니다.");
    }
  };

  // [추가] 엔터 키 감지 핸들러
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleVerify();
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col shadow-2xl border-x border-gray-100">
        
        {/* 상단 네비게이션 */}
        <div className="flex items-center px-5 py-4 relative">
            <button onClick={() => onNavigate('profile')} className="text-xl p-2 absolute left-4">✕</button>
            <h1 className="text-lg font-bold w-full text-center">비밀번호 확인</h1>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center px-8 pb-32">
            <div className="w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center mb-6 overflow-hidden">
                <img src={pandaImg} alt="Security" className="w-16 opacity-50" />
            </div>
            
            <h2 className="text-lg font-bold text-gray-800 mb-2">본인 확인</h2>
            <p className="text-sm text-gray-500 mb-8 text-center">
                회원님의 소중한 정보 보호를 위해<br/>비밀번호를 다시 한 번 확인합니다.
            </p>

            <input 
              type="password" 
              placeholder="비밀번호 입력"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(null); }}
              onKeyDown={handleKeyDown} // [수정] 엔터 키 이벤트 연결
              className="w-full py-4 px-5 bg-gray-50 border border-gray-200 rounded-2xl font-bold text-[15px] outline-none focus:border-blue-500 focus:bg-white transition-all mb-3"
            />
            
            {error && <p className="text-red-500 text-xs font-bold mb-4">{error}</p>}

            <button 
              onClick={handleVerify}
              className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-bold text-[16px] shadow-lg active:scale-[0.98] transition-transform"
            >
              확인
            </button>
        </div>
      </div>
    </div>
  );
}

export default PasswordConfirmScreen;