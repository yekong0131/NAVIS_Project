import React from 'react';

const ResultModal = ({ onRetry }) => {
  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        <h2 style={styles.title}>분석 결과</h2>
        <p style={styles.message}>바다를 인지하지 못했습니다.</p>
        
        {/* 다시 촬영 버튼 */}
        <button style={styles.button} onClick={onRetry}>
          다시 촬영
        </button>
      </div>
    </div>
  );
};

const styles = {
  overlay: {
    position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
    backgroundColor: 'rgba(0, 0, 0, 0.4)', // 배경을 좀 더 어둡게 해서 집중도 높임
    display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 2000
  },
  card: {
    backgroundColor: 'white',
    width: '80%', maxWidth: '300px', padding: '40px 20px',
    borderRadius: '30px', textAlign: 'center',
    boxShadow: '0 10px 25px rgba(0,0,0,0.2)'
  },
  title: { fontSize: '20px', fontWeight: 'bold', marginBottom: '15px', color: '#333' },
  message: { fontSize: '15px', color: '#666', marginBottom: '30px' },
  button: {
    width: '100%', padding: '15px', backgroundColor: '#4285F4', // 파란색 버튼
    color: 'white', border: 'none', borderRadius: '15px',
    fontSize: '16px', fontWeight: 'bold', cursor: 'pointer'
  }
};

export default ResultModal;