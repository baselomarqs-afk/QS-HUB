import React from 'react';
import ReactDOM from 'react-dom';

export default function LoadingOverlay({ isLoading, text, subtext, progress, isArabic }) {
  if (!isLoading) return null;

  return ReactDOM.createPortal(
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 999999,
      color: 'white',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Sleek Spinner / Radar */}
      <div style={{
        width: '80px',
        height: '80px',
        border: '4px solid rgba(59, 130, 246, 0.2)',
        borderTopColor: '#3b82f6',
        borderRadius: '50%',
        animation: 'spin-loading 1s linear infinite',
        marginBottom: '20px',
        boxShadow: '0 0 15px rgba(59, 130, 246, 0.5)'
      }} />

      <style>
        {`
          @keyframes spin-loading {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          @keyframes pulse-loading {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
          @keyframes progress-indeterminate-loading {
            0% { left: -40%; }
            100% { left: 100%; }
          }
        `}
      </style>

      <h2 style={{
        fontSize: '1.5rem',
        fontWeight: 700,
        margin: '0 0 10px 0',
        animation: 'pulse-loading 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
      }}>
        {text || (isArabic ? 'جاري المعالجة...' : 'Processing...')}
      </h2>
      
      {subtext && (
        <p style={{
          fontSize: '0.95rem',
          color: '#94a3b8',
          margin: 0,
          maxWidth: '400px',
          textAlign: 'center',
          minHeight: '44px' // prevent jittering if text wraps
        }}>
          {subtext}
        </p>
      )}

      {/* Progress Bar Track */}
      <div style={{
        width: '300px',
        height: '6px',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        borderRadius: '10px',
        marginTop: '30px',
        overflow: 'hidden',
        position: 'relative'
      }}>
        <div style={{
          position: 'absolute',
          top: 0, left: 0, bottom: 0,
          width: progress !== null && progress !== undefined ? `${progress}%` : '40%',
          backgroundColor: '#3b82f6',
          borderRadius: '10px',
          animation: progress !== null && progress !== undefined ? 'none' : 'progress-indeterminate-loading 1.5s ease-in-out infinite',
          boxShadow: '0 0 10px #3b82f6',
          transition: 'width 0.3s ease-out'
        }} />
      </div>
      
      {progress !== null && progress !== undefined && (
        <div style={{ marginTop: '10px', fontSize: '0.9rem', fontWeight: 600, color: '#3b82f6' }}>
          {progress}%
        </div>
      )}
    </div>,
    document.body
  );
}
