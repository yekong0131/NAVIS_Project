import React, { useState, useEffect, useCallback } from 'react'; // useCallback 추가
import axios from 'axios'; 
import dphoImg from "../assets/dpho.jpg"; 
import BottomTab from '../components/BottomTab';
import TopBar from "../components/TopBar";

const AREA_HIERARCHY = {
  "인천": ["전체", "강화군", "남구", "동구", "서구", "옹진군", "중구", "계양구", "남동구", "부평구", "연수구"],
  "경기": ["전체", "안산시", "시흥시", "화성시", "평택시", "김포시", "수원시", "안양시"],
  "충남": ["전체", "보령시", "서천군", "태안군", "홍성군", "서산시", "당진시"],
  "전북": ["전체", "군산시", "부안군", "고창군", "김제시"],
  "전남": ["전체", "여수시", "고흥군", "완도군", "진도군", "목포시", "신안군", "해남군", "강진군"],
  "강원": ["전체", "강릉시", "속초시", "양양군", "고성군", "동해시", "삼척시"],
  "경북": ["전체", "포항시", "경주시", "영덕군", "울진군", "울릉군"],
  "경남": ["전체", "창원시", "통영시", "거제시", "사천시", "남해군", "고성군", "하동군"],
  "부산": ["전체", "기장군", "강서구", "해운대구", "사하구", "영도구", "남구"],
  "제주": ["전체", "제주시", "서귀포시"]
};

const FILTER_OPTIONS = {
  coast: ["서해안", "남해안", "동해안", "제주도"],
  fish: ["쭈꾸미", "갑오징어", "광어", "우럭", "참돔", "문어", "갈치"]
};

function BoatSearchScreen({ onNavigate, user }) {
  const [filters, setFilters] = useState({
    area: [], 
    coast: [],
    fish: [],
    date: "",
    people: 1
  });

  const [activeFilters, setActiveFilters] = useState(filters);
  const [boats, setBoats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const [activeModal, setActiveModal] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false); 

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  useEffect(() => {
    const savedState = sessionStorage.getItem('boatSearchState');
    if (savedState) {
      const parsedState = JSON.parse(savedState);
      setFilters(parsedState.filters);
      setActiveFilters(parsedState.activeFilters);
      setBoats(parsedState.boats);
      setPage(parsedState.page);
      setHasNext(parsedState.hasNext);
      setHasSearched(parsedState.hasSearched);
    }
  }, []);

  useEffect(() => {
    if (hasSearched) {
      const stateToSave = {
        filters,
        activeFilters,
        boats,
        page,
        hasNext,
        hasSearched
      };
      sessionStorage.setItem('boatSearchState', JSON.stringify(stateToSave));
    }
  }, [filters, activeFilters, boats, page, hasNext, hasSearched]);

  const fetchBoats = async (pageNo, isReset = false, targetFilters) => {
    if (loading && !isReset) return;

    setLoading(true);
    setError(null);
    try {
      const params = {
        people: targetFilters.people,
        page: pageNo,
        page_size: 10,
      };

      if (targetFilters.area.length > 0) {
        const firstArea = targetFilters.area[0];
        const [main, sub] = firstArea.split(" ");
        params.area_main = main;
        if (sub && sub !== "전체") params.area_sub = sub;
      }
      
      if (targetFilters.coast.length > 0) {
        const rawSea = targetFilters.coast[0];
        params.area_sea = rawSea.replace("안", "").replace("도", ""); 
      }

      if (targetFilters.fish.length > 0) params.fish = targetFilters.fish[0];
      if (targetFilters.date) params.date = targetFilters.date;

      const response = await axios.get(`${API_URL}/boats/search/`, { params });
      
      if (response.data.status === 'success') {
        const newResults = response.data.results;
        const pagination = response.data.pagination;

        setBoats(prev => isReset ? newResults : [...prev, ...newResults]);
        setHasNext(pagination.has_next);
        setHasSearched(true);
      }
    } catch (err) {
      console.error("선박 검색 오류:", err);
      setError("데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchClick = useCallback(() => {
    setActiveFilters({ ...filters }); 
    setPage(1);
    setBoats([]); 
    fetchBoats(1, true, filters);
  }, [filters]);

  // [추가] 엔터 키 감지 (모달이 닫혀있을 때만 동작)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && !activeModal && !isModalOpen) {
        handleSearchClick();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSearchClick, activeModal, isModalOpen]);

  const handleLoadMore = () => {
    if (hasNext && !loading) {
        const nextPage = page + 1;
        setPage(nextPage);
        fetchBoats(nextPage, false, activeFilters);
    }
  };

  const toggleFilter = (type, value) => {
    setFilters(prev => {
      const current = prev[type];
      if (current.includes(value)) {
        return { ...prev, [type]: current.filter(item => item !== value) };
      } else {
        return { ...prev, [type]: [...current, value] };
      }
    });
  };

  const removeFilter = (type, value) => {
    if (type === 'area' && value.endsWith(' 전체')) {
        const mainArea = value.split(' ')[0];
        setFilters(prev => ({
            ...prev,
            area: prev.area.filter(item => !item.startsWith(mainArea))
        }));
    } else {
        setFilters(prev => ({ ...prev, [type]: prev[type].filter(item => item !== value) }));
    }
  };

  const handleGoHome = () => {
      sessionStorage.removeItem('boatSearchState');
      onNavigate('home');
  };

  return (
    <div className="fixed inset-0 bg-slate-100 flex justify-center overflow-hidden font-sans">
      <div className="relative w-full max-w-[420px] h-full bg-slate-50 flex flex-col overflow-hidden shadow-2xl border-x border-gray-100">
        
        {/* 상단 헤더 & 필터 영역 */}
        <TopBar user={user} onNavigate={onNavigate} />
        <div className="bg-white shadow-sm z-10 shrink-0">
            <div className="px-5 pt-4 pb-5 flex items-center justify-center">
                <h1 className="text-lg font-bold text-black">선박 조회</h1>
            </div>

            <div className="px-4 pb-2">
                <div className="flex gap-2 overflow-x-auto no-scrollbar pb-2">
                    <FilterButton label="지역" isActive={filters.area.length > 0} onClick={() => setActiveModal('area')} />
                    <FilterButton label="해안" isActive={filters.coast.length > 0} onClick={() => setActiveModal('coast')} />
                    <FilterButton label="날짜" isActive={!!filters.date} onClick={() => setActiveModal('date')} />
                    <FilterButton label="어종" isActive={filters.fish.length > 0} onClick={() => setActiveModal('fish')} />
                    <FilterButton label={`${filters.people}명`} isActive={true} onClick={() => setActiveModal('people')} />
                </div>

                <div className="flex flex-wrap gap-1.5 mt-1 min-h-[4px]">
                    {(() => {
                        const areaGroups = {};
                        filters.area.forEach(tag => {
                            const main = tag.split(' ')[0];
                            if (!areaGroups[main]) areaGroups[main] = [];
                            areaGroups[main].push(tag);
                        });
                        return Object.entries(areaGroups).flatMap(([main, tags]) => {
                            const allKey = `${main} 전체`;
                            if (tags.includes(allKey)) {
                                return <FilterTag key={allKey} label={allKey} onRemove={() => removeFilter('area', allKey)} />;
                            }
                            return tags.map(tag => (
                                <FilterTag key={tag} label={tag} onRemove={() => removeFilter('area', tag)} />
                            ));
                        });
                    })()}
                    {filters.coast.map(v => <FilterTag key={v} label={v} onRemove={() => removeFilter('coast', v)} />)}
                    {filters.fish.map(v => <FilterTag key={v} label={v} onRemove={() => removeFilter('fish', v)} />)}
                    {filters.date && (
                        <FilterTag label={filters.date} onRemove={() => setFilters(prev => ({ ...prev, date: "" }))} />
                    )}
                </div>
            </div>

            <div className="px-4 pb-4 mt-2">
                <button 
                    onClick={handleSearchClick}
                    className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold text-[15px] shadow-md active:scale-[0.98] transition-all flex items-center justify-center gap-2"
                >
                    🔍 조건에 맞는 선박 조회
                </button>
            </div>
        </div>

        {/* 선박 리스트 영역 */}
        <div className="flex-1 overflow-y-auto px-4 py-4 pb-32 no-scrollbar">
          
          {!hasSearched && !loading && boats.length === 0 && (
             <div className="flex flex-col justify-center items-center h-60 text-gray-400">
                <span className="text-4xl mb-3">⚓️</span>
                <span className="font-bold mb-1">원하는 조건으로 검색해보세요!</span>
                <span className="text-xs">지역, 날짜, 어종 등을 선택하고 조회 버튼을 눌러주세요.</span>
             </div>
          )}

          {loading && boats.length === 0 && (
             <div className="flex justify-center items-center h-40">
                <span className="text-gray-400 animate-pulse">배를 찾고 있습니다... 🌊</span>
             </div>
          )}
          
          {hasSearched && !loading && !error && boats.length === 0 && (
             <div className="text-center py-20 text-gray-400 bg-gray-50 rounded-xl mx-2">
                <div className="text-2xl mb-2">텅...</div>
                <span>조건에 맞는 배를 찾지 못했어요.</span>
             </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {boats.map((boat) => (
              <div 
                key={boat.boat_id} 
                onClick={() => onNavigate("boat-detail", { ...boat, fromPage: 'boat-search' })} 
                className="bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 active:scale-95 transition-transform cursor-pointer flex flex-col h-full"
              >
                <div className="w-full h-32 bg-gray-200 relative">
                  <img 
                    src={boat.main_image_url || dphoImg} 
                    alt={boat.name} 
                    className="w-full h-full object-cover" 
                    onError={(e) => { 
                        e.target.onerror = null; 
                        e.target.src = dphoImg; 
                    }}
                  />
                  <div className="absolute top-2 right-2 bg-black/60 backdrop-blur-sm px-2 py-0.5 rounded-md">
                     <span className="text-[10px] font-bold text-white">{boat.area_sea || "기타"}</span>
                  </div>
                </div>
                <div className="p-3 flex flex-col flex-1 justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-1">
                      <h3 className="font-bold text-[15px] text-gray-900 leading-tight">{boat.name}</h3>
                    </div>
                    <p className="text-[11px] text-gray-500 mb-2 truncate">
                        {boat.area_main} {boat.area_sub} · {boat.port}
                    </p>
                    <div className="flex gap-1 flex-wrap mb-2">
                      {boat.target_fish && boat.target_fish.split(',').slice(0, 2).map((fish, i) => (
                        <span key={i} className="text-[10px] bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-md font-medium">#{fish.trim()}</span>
                      ))}
                    </div>
                  </div>
                  
                  {boat.nearest_schedule ? (
                      <div className="pt-2 border-t border-gray-50">
                        <div className="flex justify-between items-center mb-0.5">
                          <span className="text-[10px] text-red-500 font-bold">
                            {boat.nearest_schedule.sdate.substring(5).replace('-', '.')}
                          </span>
                          <span className="text-[10px] text-gray-400 font-medium">
                            {boat.nearest_schedule.remain_embarkation_num}석 남음
                          </span>
                        </div>
                        <div className="text-right">
                          <span className="font-bold text-[15px] text-gray-900">
                            {Number(boat.nearest_schedule.price).toLocaleString()}원
                          </span>
                        </div>
                      </div>
                  ) : (
                      <div className="pt-2 border-t border-gray-50 text-center">
                          <span className="text-[10px] text-gray-400">일정 없음</span>
                      </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {hasNext && (
            <div className="mt-6 mb-4 flex justify-center">
                <button 
                    onClick={handleLoadMore}
                    disabled={loading}
                    className="px-6 py-3 bg-gray-100 rounded-full text-sm font-bold text-gray-600 hover:bg-gray-200 active:scale-95 transition-all flex items-center gap-2"
                >
                    {loading ? "불러오는 중..." : "더 보기 ⬇"}
                </button>
            </div>
          )}
        </div>

        {/* ... (모달 및 하단 탭은 기존 코드 사용) ... */}
        {activeModal && (
          <FilterModal 
            type={activeModal} 
            options={FILTER_OPTIONS}
            areaHierarchy={AREA_HIERARCHY}
            selected={filters} 
            onSelect={toggleFilter}
            setFilters={setFilters}
            onClose={() => setActiveModal(null)} 
          />
        )}

        <BottomTab 
          activeTab="boat-search"          
          onNavigate={onNavigate}          
          onCameraClick={() => setIsModalOpen(true)} 
        />

        {isModalOpen && (
          <div className="absolute inset-0 z-[100] flex items-end justify-center px-4 pb-12 transition-all">
            <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={() => setIsModalOpen(false)}></div>
            <div className="relative w-full bg-white rounded-[32px] overflow-hidden shadow-2xl p-8 animate-in slide-in-from-bottom duration-300">
              <p className="text-center text-gray-800 font-bold mb-8 text-[15px]">입력할 방법을 선택해주세요.</p>
              <div className="flex justify-around items-center">
                <button onClick={() => { setIsModalOpen(false); onNavigate('home'); }} className="flex flex-col items-center gap-3">
                  <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center text-3xl shadow-sm border border-gray-100">📷</div>
                  <span className="text-[13px] font-bold text-gray-600">카메라</span>
                </button>
                <button onClick={() => setIsModalOpen(false)} className="flex flex-col items-center gap-3">
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

// ... 서브 컴포넌트(FilterButton, FilterTag, FilterModal)는 기존 코드와 동일 ...
const FilterButton = ({ label, isActive, onClick }) => (
  <button 
    onClick={onClick}
    className={`px-3 py-1.5 rounded-full text-[12px] font-bold whitespace-nowrap transition-colors border ${
      isActive ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200'
    }`}
  >
    {label} ▼
  </button>
);

const FilterTag = ({ label, onRemove }) => (
  <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-gray-100 text-[10px] font-medium text-gray-600 border border-gray-200">
    {label}
    <button onClick={(e) => { e.stopPropagation(); onRemove(); }} className="ml-1 text-gray-400 hover:text-gray-600">×</button>
  </span>
);

const FilterModal = ({ type, options, areaHierarchy, selected, onSelect, setFilters, onClose }) => {
    // ... (기존 FilterModal 코드 사용) ...
    const [currentMainArea, setCurrentMainArea] = useState("인천"); 
    const [tempSelectedAreas, setTempSelectedAreas] = useState([...selected.area]); 

    const toggleTempArea = (main, sub) => {
        const fullValue = `${main} ${sub}`; 
        const subAreas = areaHierarchy[main] || [];
        const allSubValues = subAreas.map(s => `${main} ${s}`);
        const allKey = `${main} 전체`;

        if (sub === "전체") {
            const isAllSelected = tempSelectedAreas.includes(allKey);
            if (isAllSelected) {
                setTempSelectedAreas(prev => prev.filter(item => !allSubValues.includes(item)));
            } else {
                setTempSelectedAreas(prev => {
                    const otherAreas = prev.filter(item => !allSubValues.includes(item));
                    return [...otherAreas, ...allSubValues];
                });
            }
        } else {
            let newSelected = [...tempSelectedAreas];
            if (newSelected.includes(fullValue)) {
                newSelected = newSelected.filter(item => item !== fullValue);
                newSelected = newSelected.filter(item => item !== allKey);
            } else {
                newSelected.push(fullValue);
                const specificSubValues = allSubValues.filter(v => v !== allKey);
                const allSpecificSelected = specificSubValues.every(v => newSelected.includes(v));
                if (allSpecificSelected) {
                    if (!newSelected.includes(allKey)) newSelected.push(allKey);
                }
            }
            setTempSelectedAreas(newSelected);
        }
    };

    const applyAreaFilter = () => {
        setFilters(prev => ({ ...prev, area: tempSelectedAreas }));
        onClose();
    };

    const resetAreaFilter = () => {
        setTempSelectedAreas([]);
    };

    if (type === 'area') {
        const mainAreas = Object.keys(areaHierarchy);
        const subAreas = areaHierarchy[currentMainArea] || [];
        return (
            <div className="absolute inset-0 z-50 flex items-end justify-center">
                <div className="absolute inset-0 bg-black/40" onClick={onClose}></div>
                <div className="relative w-full h-[600px] bg-white rounded-t-[32px] flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-300">
                    <div className="flex items-center justify-center h-14 border-b border-gray-100 relative shrink-0">
                        <button onClick={onClose} className="absolute left-4 p-2 text-2xl">✕</button>
                        <span className="font-bold text-lg">지역선택</span>
                    </div>
                    <div className="flex flex-1 overflow-hidden">
                        <ul className="w-1/3 overflow-y-auto bg-white border-r border-gray-100">
                            {mainAreas.map(area => (
                                <li key={area} onClick={() => setCurrentMainArea(area)} className={`py-4 text-center text-[15px] cursor-pointer transition-colors ${currentMainArea === area ? 'bg-gray-50 text-blue-600 font-bold' : 'text-gray-600 hover:bg-gray-50'}`}>{area}</li>
                            ))}
                        </ul>
                        <ul className="w-2/3 overflow-y-auto bg-gray-50 p-2">
                            {subAreas.map((sub, idx) => {
                                const fullValue = `${currentMainArea} ${sub}`;
                                const isSelected = tempSelectedAreas.includes(fullValue);
                                const fixedCount = sub === "전체" ? 35 : ((sub.length * 7 + idx) % 20) + 1;
                                return (
                                    <li key={sub} onClick={() => toggleTempArea(currentMainArea, sub)} className="py-3 px-4 mb-1 flex items-center justify-between cursor-pointer rounded-lg hover:bg-gray-100">
                                        <span className={`${isSelected ? 'text-blue-600 font-bold' : 'text-gray-700'}`}>{sub} <span className="text-gray-400 font-normal">({fixedCount})</span></span>
                                        {isSelected && <span className="text-blue-600 font-bold">✓</span>}
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                    <div className="p-4 border-t border-gray-100 flex gap-3 shrink-0 bg-white pb-8">
                        <button onClick={resetAreaFilter} className="flex-1 py-3.5 rounded-full border border-gray-300 text-gray-600 font-bold text-[15px]">초기화</button>
                        <button onClick={applyAreaFilter} className="flex-1 py-3.5 rounded-full bg-gray-200 text-gray-500 font-bold text-[15px] hover:bg-black hover:text-white transition-colors">적용</button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="absolute inset-0 z-50 flex items-end justify-center">
            <div className="absolute inset-0 bg-black/40" onClick={onClose}></div>
            <div className="relative w-full bg-white rounded-t-[32px] p-6 animate-in slide-in-from-bottom duration-300">
                <div className="flex justify-between items-center mb-5">
                    <h3 className="text-[16px] font-bold text-gray-900">{type === 'coast' ? '해안 선택' : type === 'fish' ? '어종 선택' : type === 'date' ? '날짜 선택' : '인원 선택'}</h3>
                    <button onClick={onClose} className="text-gray-400 text-lg">✕</button>
                </div>
                <div className="max-h-[300px] overflow-y-auto no-scrollbar">
                    {type === 'date' ? (
                        <input type="date" className="w-full p-3 border border-gray-200 rounded-xl text-md bg-gray-50 outline-none focus:border-blue-500" value={selected.date} onChange={(e) => setFilters(prev => ({ ...prev, date: e.target.value }))} />
                    ) : type === 'people' ? (
                        <div className="flex items-center justify-center gap-6 py-4">
                            <button className="w-10 h-10 rounded-full bg-gray-100 text-lg font-bold" onClick={() => setFilters(prev => ({ ...prev, people: Math.max(1, prev.people - 1) }))}>-</button>
                            <span className="text-xl font-bold">{selected.people}명</span>
                            <button className="w-10 h-10 rounded-full bg-gray-100 text-lg font-bold" onClick={() => setFilters(prev => ({ ...prev, people: prev.people + 1 }))}>+</button>
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-2">
                            {options[type].map(opt => (
                                <button key={opt} onClick={() => onSelect(type, opt)} className={`px-3 py-2.5 rounded-xl text-[13px] font-bold transition-all border ${selected[type].includes(opt) ? 'bg-blue-600 text-white border-blue-600 shadow-sm' : 'bg-white text-gray-500 border-gray-100'}`}>{opt}</button>
                            ))}
                        </div>
                    )}
                </div>
                <button onClick={onClose} className="w-full mt-6 py-3.5 bg-gray-900 text-white rounded-2xl font-bold text-[15px] active:scale-[0.98]">선택 완료</button>
            </div>
        </div>
    );
};

export default BoatSearchScreen;