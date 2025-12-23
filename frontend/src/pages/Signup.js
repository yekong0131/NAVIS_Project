import React, { useState, useEffect } from "react"; // [수정] useEffect 추가
import axios from "axios";
import pandaLoginImg from "../assets/login_panda.png"; 

function Signup({ onNavigate }) {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    confirmPassword: "",
    nickname: "",
  });

  const [emailId, setEmailId] = useState("");
  const [emailDomain, setEmailDomain] = useState("");
  const [error, setError] = useState(null);

  // [추가] 캐릭터 관련 State
  const [characters, setCharacters] = useState([]); // 캐릭터 목록
  const [selectedCharId, setSelectedCharId] = useState(null); // 선택된 ID

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  const domains = [
    "naver.com", "gmail.com", "daum.net", "kakao.com", "hanmail.net", "nate.com"
  ];

  // [추가] 1. 페이지 로드 시 캐릭터 목록 불러오기
  useEffect(() => {
    const fetchCharacters = async () => {
        try {
            const response = await axios.get(`${API_URL}/profile-characters/`);
            setCharacters(response.data);
        } catch (err) {
            console.error("캐릭터 목록 로딩 실패:", err);
        }
    };
    fetchCharacters();
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError(null);
  };

  const handleDomainSelect = (e) => {
    const value = e.target.value;
    setEmailDomain(value === "direct" ? "" : value);
  };

  const handleSignup = async () => {
    const fullEmail = emailId && emailDomain ? `${emailId}@${emailDomain}` : "";

    // 유효성 검사
    if (!formData.username || !formData.password || !formData.nickname) {
        setError("아이디, 비밀번호, 닉네임은 필수입니다. 🥺");
        return;
    }
    if (formData.password.length < 8) {
        setError("비밀번호는 최소 8자 이상이어야 합니다. 🔒");
        return;
    }
    if (formData.password !== formData.confirmPassword) {
        setError("비밀번호가 서로 일치하지 않습니다.");
        return;
    }

    try {
        const payload = {
            username: formData.username,
            password: formData.password,
            password2: formData.confirmPassword,
            nickname: formData.nickname,
            email: fullEmail,
            character_id: selectedCharId // [추가] 선택한 캐릭터 ID 전송 (없으면 null)
        };

        const response = await axios.post(`${API_URL}/auth/signup/`, payload);

        if (response.status === 201) {
            alert("회원가입 성공! 환영합니다 🎉");
            onNavigate("login");
        }
    } catch (err) {
        // ... (기존 에러 처리 로직 동일) ...
        console.error("회원가입 에러 상세:", err);
        if (err.response && err.response.data) {
             const data = err.response.data;
             let msg = "회원가입 중 오류가 발생했습니다.";
             // ... (에러 메시지 처리 로직 생략, 기존 코드 사용) ...
             if(data.detail) msg = data.detail;
             setError(msg);
        } else {
            setError("서버와 연결할 수 없습니다.");
        }
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-white flex flex-col shadow-2xl border-x border-gray-100">
        
        {/* 상단 네비게이션 */}
        <div className="flex justify-between items-center px-5 py-4 shrink-0">
            <button onClick={() => onNavigate('login')} className="text-2xl text-gray-500 p-1 -ml-2">✕</button>
            <span className="font-bold text-xl">회원가입</span>
            <div className="w-8"></div>
        </div>

        <div className="flex-1 overflow-y-auto no-scrollbar px-6 pt-2 pb-10 text-center text-black">
          
          {/* [수정] 캐릭터 선택 영역 (상단 배치) */}
          <div className="mb-6">
            <h3 className="text-sm font-bold text-gray-500 mb-3 text-left pl-1">프로필 캐릭터 선택 (선택)</h3>
            
            {/* 가로 스크롤 캐릭터 리스트 */}
            <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2 px-1">
                {/* 기본(선택안함) 옵션 */}
                <div 
                    onClick={() => setSelectedCharId(null)}
                    className={`shrink-0 flex flex-col items-center gap-2 cursor-pointer transition-all ${selectedCharId === null ? 'opacity-100 scale-105' : 'opacity-50 hover:opacity-80'}`}
                >
                    <div className={`w-20 h-20 rounded-full bg-gray-100 border-2 flex items-center justify-center overflow-hidden ${selectedCharId === null ? 'border-blue-500 shadow-md ring-2 ring-blue-100' : 'border-transparent'}`}>
                        <img src={pandaLoginImg} alt="기본" className="w-14 h-14 object-contain opacity-50" />
                    </div>
                    <span className={`text-[11px] font-bold ${selectedCharId === null ? 'text-blue-600' : 'text-gray-400'}`}>기본</span>
                </div>

                {/* API에서 불러온 캐릭터들 */}
                {characters.map((char) => (
                    <div 
                        key={char.character_id}
                        onClick={() => setSelectedCharId(char.character_id)}
                        className={`shrink-0 flex flex-col items-center gap-2 cursor-pointer transition-all ${selectedCharId === char.character_id ? 'opacity-100 scale-105' : 'opacity-60 hover:opacity-100'}`}
                    >
                        <div className={`w-20 h-20 rounded-full bg-white border-2 flex items-center justify-center overflow-hidden ${selectedCharId === char.character_id ? 'border-blue-500 shadow-md ring-2 ring-blue-100' : 'border-gray-100'}`}>
                            <img src={char.image_url} alt={char.name} className="w-full h-full object-cover" />
                        </div>
                        <span className={`text-[11px] font-bold ${selectedCharId === char.character_id ? 'text-blue-600' : 'text-gray-500'}`}>{char.name}</span>
                    </div>
                ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 px-1 mb-8">
            {error && (
                <div className="bg-red-50 text-red-500 text-[13px] py-3 rounded-xl font-bold mb-2 flex items-center justify-center animate-pulse border border-red-100">
                    ⚠️ {error}
                </div>
            )}

            {/* ... 기존 입력 필드들 (아이디, 비번 등) 그대로 유지 ... */}
            <input name="username" type="text" placeholder="아이디" value={formData.username} onChange={handleChange} className="w-full py-3.5 bg-gray-50 text-gray-900 border rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 focus:bg-white transition-colors" />
            <input name="password" type="password" placeholder="비밀번호 (8자 이상)" value={formData.password} onChange={handleChange} className="w-full py-3.5 bg-gray-50 text-gray-900 border rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 focus:bg-white transition-colors" />
            <input name="confirmPassword" type="password" placeholder="비밀번호 확인" value={formData.confirmPassword} onChange={handleChange} className="w-full py-3.5 bg-gray-50 text-gray-900 border rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 focus:bg-white transition-colors" />
            <input name="nickname" type="text" placeholder="닉네임" value={formData.nickname} onChange={handleChange} className="w-full py-3.5 bg-gray-50 text-gray-900 border rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 focus:bg-white transition-colors mt-2" />

            {/* 이메일 입력 (기존 코드 유지) */}
            <div className="mt-2">
                <div className="flex items-center gap-1 mb-2">
                    <input type="text" placeholder="이메일 ID" value={emailId} onChange={(e) => setEmailId(e.target.value)} className="w-full py-3.5 bg-gray-50 text-gray-900 border border-gray-200 rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 focus:bg-white transition-colors" />
                    <span className="text-gray-400 font-bold">@</span>
                    <input type="text" placeholder="도메인" value={emailDomain} onChange={(e) => setEmailDomain(e.target.value)} className="w-full py-3.5 bg-gray-50 text-gray-900 border border-gray-200 rounded-xl font-bold text-[15px] px-4 outline-none focus:border-blue-500 focus:bg-white transition-colors" />
                </div>
                <div className="relative">
                    <select onChange={handleDomainSelect} className="w-full py-3 bg-white text-gray-600 border border-gray-200 rounded-xl font-bold text-[14px] px-4 outline-none focus:border-blue-500 appearance-none cursor-pointer">
                        <option value="direct">직접 입력</option>
                        {domains.map(d => <option key={d} value={d}>{d}</option>)}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400 text-xs">▼</div>
                </div>
            </div>

            <button onClick={handleSignup} className="w-full py-4 bg-[#7e96ff] text-white rounded-xl font-bold text-[17px] mt-4 shadow-md active:scale-[0.98] transition-transform">가입하기</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Signup;