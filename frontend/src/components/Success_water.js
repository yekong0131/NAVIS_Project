import React from 'react';

// App.js에서 'onClose'라는 기능을 전달받아 사용합니다.
const SuccessWater = ({ onClose }) => {
  return (
    <div style={styles.container}>
      <div style={styles.toastCard}>
        {/* 왼쪽 체크 아이콘 */}
        <span style={styles.icon}>✔️</span>
        
        {/* 중앙 문구 */}
        <span style={styles.text}>성공적으로 물색을 인식했어요</span>
        
        {/* 오른쪽 닫기(X) 버튼 */}
        <button onClick={onClose} style={styles.closeBtn}>
          ✕
        </button>
      </div>
    </div>
  );
};

// 이미지 UI와 똑같이 보이게 하는 디자인 설정
const styles = {
  container: {
    position: 'absolute',
    top: '60px', // 휴대폰 상태표시줄 아래 적당한 위치
    left: '50%',
    transform: 'translateX(-50%)',
    width: '90%',
    zIndex: 3000,
  },
  toastCard: {
    backgroundColor: 'rgba(212, 237, 218, 0.9)', // 연한 초록색 (이미지 느낌)
    border: '1px solid #c3e6cb',
    borderRadius: '8px',
    padding: '10px 15px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
  },
  icon: {
    color: '#155724',
    fontSize: '14px',
    marginRight: '10px',
  },
  text: {
    flex: 1,
    fontSize: '13px',
    color: '#155724',
    fontWeight: '500',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: '16px',
    color: '#155724',
    cursor: 'pointer',
    padding: '0 5px',
  },
};

// 중요: 파일명과 상관없이 밖에서 'SuccessWater'라는 이름으로 쓸 수 있게 보냅니다.
export default SuccessWater;