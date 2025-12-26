import React, { useState, useEffect } from "react";
import axios from "axios";
import TopBar from "../components/TopBar";

function UserProfileEditScreen({ user, onNavigate, onUserUpdate }) {
  // 1. 상태 관리
  const [nickname, setNickname] = useState("");
  const [emailId, setEmailId] = useState("");
  const [emailDomain, setEmailDomain] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  
  // 캐릭터 관련
  const [characters, setCharacters] = useState([]);
  const [selectedCharId, setSelectedCharId] = useState(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
  
  const domains = [
    "naver.com", "gmail.com", "daum.net", "kakao.com", "hanmail.net", "nate.com"
  ];

  // 2. 초기 데이터 세팅 (캐릭터 목록 + 내 정보)
  useEffect(() => {
    // 캐릭터 목록 불러오기
    const fetchCharacters = async () => {
        try {
            const response = await axios.get(`${API_URL}/profile-characters/`);
            setCharacters(response.data);
        } catch (err) {
            console.error("캐릭터 목록 로딩 실패:", err);
        }
    };
    fetchCharacters();

    // 기존 유저 정보 채우기
    if (user) {
        setNickname(user.nickname || "");
        
        // 이메일 분리 (id @ domain)
        if (user.email) {
            const [id, domain] = user.email.split('@');
            setEmailId(id || "");
            setEmailDomain(domain || "");
        }
        
        // [핵심] 현재 설정된 캐릭터 ID가 있으면 그것을 선택 상태로 설정
        if (user.profile_character_id) {
            setSelectedCharId(user.profile_character_id);
        } else {
            setSelectedCharId(null); // 없으면 기본(null)
        }
    }
  }, [user]);

  const handleDomainSelect = (e) => {
    const value = e.target.value;
    setEmailDomain(value === "direct" ? "" : value);
  };

  const handleUpdate = async () => {
    // 유효성 검사
    if (!nickname) {
        alert("닉네임은 필수입니다.");
        return;
    }
    
    // 비밀번호 변경 시 확인
    if (password && password !== confirmPassword) {
        alert("새 비밀번호가 일치하지 않습니다.");
        return;
    }

    const fullEmail = emailId && emailDomain ? `${emailId}@${emailDomain}` : "";

    try {
        const token = localStorage.getItem('authToken');
        
        // 보낼 데이터 구성 (값이 있는 것만 보냄)
        const payload = {
            nickname: nickname,
            email: fullEmail,
            // 비밀번호는 입력했을 때만 전송
            ...(password && { password: password }),
            // 캐릭터는 선택했을 때만 전송
            ...(selectedCharId && { character_id: selectedCharId })
        };

        const response = await axios.patch(
            `${API_URL}/auth/me/update/`, 
            payload,
            { headers: { Authorization: `Token ${token}` } }
        );

        if (response.status === 200) {
            alert("회원 정보가 수정되었습니다! 🎉");
            
            // [중요] 앱 전역의 user 상태 업데이트
            if (onUserUpdate && response.data.user) {
                onUserUpdate(response.data.user);
            }
            
            onNavigate('home');
        }
    } catch (err) {
        console.error("수정 실패:", err);
        alert("정보 수정 중 오류가 발생했습니다.");
    }
  };

  // [추가] 엔터 키 감지 핸들러
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleUpdate();
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col shadow-2xl border-x border-gray-100">
        
        {/* 헤더 */}
        <div className="flex items-center px-5 py-4 border-b border-gray-100 relative">
            <button 
                onClick={() => onNavigate('home')} 
                className="text-xl p-2 absolute left-4"
            >
                〈
            </button>
            <h1 className="text-lg font-bold w-full text-center">회원 정보 수정</h1>
        </div>

        <div className="flex-1 overflow-y-auto no-scrollbar px-6 py-6 pb-20">
          
          {/* 1. 프로필 캐릭터 변경 */}
          <div className="mb-8">
            <h3 className="text-sm font-bold text-gray-500 mb-3 ml-1">프로필 캐릭터 변경</h3>
            <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2 px-1">
                {/* 기본(해제) 옵션 */}
                <div 
                    onClick={() => setSelectedCharId(null)}
                    className={`shrink-0 flex flex-col items-center gap-2 cursor-pointer opacity-60 hover:opacity-100`}
                >
                     <div className="w-16 h-16 rounded-full bg-gray-100 border-2 border-gray-200 flex items-center justify-center">
                        <span className="text-xs font-bold text-gray-400">기본</span>
                     </div>
                </div>

                {characters.map((char) => (
                    <div 
                        key={char.character_id}
                        onClick={() => setSelectedCharId(char.character_id)}
                        className={`shrink-0 flex flex-col items-center gap-2 cursor-pointer transition-all ${selectedCharId === char.character_id ? 'scale-105' : 'opacity-60 hover:opacity-100'}`}
                    >
                        <div className={`w-16 h-16 rounded-full bg-white border-2 flex items-center justify-center overflow-hidden ${selectedCharId === char.character_id ? 'border-blue-500 ring-2 ring-blue-100' : 'border-gray-100'}`}>
                            <img src={char.image_url} alt={char.name} className="w-full h-full object-cover" />
                        </div>
                    </div>
                ))}
            </div>
          </div>

          {/* 2. 텍스트 정보 입력 */}
          <div className="space-y-5">
            <div>
                <label className="block text-xs font-bold text-gray-400 mb-1 ml-1">닉네임</label>
                <input 
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
                  className="w-full py-3.5 bg-gray-50 border border-gray-200 rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 transition-colors"
                />
            </div>

            <div>
                <label className="block text-xs font-bold text-gray-400 mb-1 ml-1">이메일</label>
                <div className="flex items-center gap-1 mb-2">
                    <input 
                        type="text"
                        placeholder="ID"
                        value={emailId}
                        onChange={(e) => setEmailId(e.target.value)}
                        onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
                        className="w-full py-3.5 bg-gray-50 border border-gray-200 rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500"
                    />
                    <span className="text-gray-400">@</span>
                    <input 
                        type="text"
                        placeholder="Domain"
                        value={emailDomain}
                        onChange={(e) => setEmailDomain(e.target.value)}
                        onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
                        className="w-full py-3.5 bg-gray-50 border border-gray-200 rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500"
                    />
                </div>
                <select 
                    onChange={handleDomainSelect}
                    className="w-full py-3 bg-white text-gray-600 border border-gray-200 rounded-xl font-bold text-[14px] px-4 outline-none"
                >
                    <option value="direct">직접 입력</option>
                    {domains.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
            </div>

            <div className="pt-4 border-t border-gray-100">
                <label className="block text-xs font-bold text-gray-400 mb-1 ml-1">새 비밀번호 (변경 시에만 입력)</label>
                <input 
                  type="password"
                  placeholder="변경할 비밀번호"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
                  className="w-full py-3.5 bg-gray-50 border border-gray-200 rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 mb-3"
                />
                <input 
                  type="password"
                  placeholder="비밀번호 확인"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  onKeyDown={handleKeyDown} // [추가] 엔터 키 이벤트 연결
                  className={`w-full py-3.5 bg-gray-50 border rounded-xl font-bold text-[15px] px-4 outline-none transition-colors ${
                      confirmPassword && password !== confirmPassword 
                      ? 'border-red-500' 
                      : 'border-gray-200 focus:border-blue-500'
                  }`}
                />
            </div>
          </div>
        </div>

        {/* 하단 저장 버튼 */}
        <div className="absolute bottom-0 left-0 w-full bg-white border-t border-gray-100 p-5">
            <button 
              onClick={handleUpdate}
              className="w-full py-4 bg-indigo-600 text-white rounded-xl font-bold text-[17px] shadow-lg active:scale-[0.98] transition-transform"
            >
              저장하기
            </button>
        </div>

      </div>
    </div>
  );
}

export default UserProfileEditScreen;