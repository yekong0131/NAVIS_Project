import React from 'react';

// progress는 0~100 사이의 숫자입니다.
const AnalysisModal = ({ progress }) => {
  return (
    <div style={styles.overlay}>
      <div style={styles.modalCard}>
        {/* 상단 스피너 아이콘 (이미지 속 로딩 모양) */}
        <div style={styles.spinner}>
          <svg width="40" height="40" viewBox="0 0 50 50">
            <circle cx="25" cy="25" r="20" fill="none" stroke="#ccc" strokeWidth="5" />
            <path d="M25 5 A20 20 0 0 1 45 25" fill="none" stroke="#666" strokeWidth="5" />
          </svg>
        </div>

        {/* 텍스트 영역: 좌측 문구, 우측 퍼센트 */}
        <div style={styles.textContainer}>
          <span style={styles.mainText}>현재 물색을 분석 중..</span>
          <span style={styles.percentText}>{progress}%</span>
        </div>

        {/* 하단 프로그레스 바 배경 */}
        <div style={styles.progressBackground}>
          {/* 실제로 차오르는 바 (progress 값에 따라 길어짐) */}
          <div style={{ ...styles.progressBar, width: `${progress}%` }}></div>
        </div>
      </div>
    </div>
  );
};

// 이미지 UI와 똑같이 보이게 하는 디자인 설정
const styles = {
  overlay: {
    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.2)', // 반투명 배경
    backdropFilter: 'blur(4px)', // 배경 흐리게
    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000
  },
  modalCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)', // 하얀색 투명 박스
    width: '85%', maxWidth: '320px', padding: '30px 20px',
    borderRadius: '20px', textAlign: 'center',
    boxShadow: '0 4px 15px rgba(0,0,0,0.1)'
  },
  spinner: { marginBottom: '20px' },
  textContainer: {
    display: 'flex', justifyContent: 'space-between', 
    alignItems: 'center', marginBottom: '10px', padding: '0 5px'
  },
  mainText: { fontSize: '15px', fontWeight: 'bold', color: '#333' },
  percentText: { fontSize: '14px', color: '#666' },
  progressBackground: {
    height: '4px', backgroundColor: '#E0E0E0', borderRadius: '10px', overflow: 'hidden'
  },
  progressBar: {
    height: '100%', backgroundColor: '#2E7D32', // 진한 초록색 바
    transition: 'width 0.2s ease-out'
  }
};

export default AnalysisModal;