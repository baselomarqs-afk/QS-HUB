import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import logo from '../assets/logo.png';

export default function Auth({ onLoginSuccess, isArabic }) {
  const [isLogin, setIsLogin] = useState(true);
  const [isForgot, setIsForgot] = useState(false);
  const [isVerify, setIsVerify] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const API_URL = "/api/auth";

  const handleVerifyEmail = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code: verifyCode.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || (isArabic ? 'رمز التأكيد غير صحيح أو منتهي الصلاحية.' : 'Invalid or expired verification code.'));
      localStorage.setItem('qto_token', data.token);
      localStorage.setItem('qto_user', JSON.stringify(data.user));
      onLoginSuccess(data.token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/resend-verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || (isArabic ? 'تعذّر إعادة إرسال الرمز.' : 'Could not resend code.'));
      setMessage(isArabic ? 'تم إرسال رمز تأكيد جديد (6 أرقام) إلى بريدك الإلكتروني.' : (data.message || 'A new 6-digit verification code was sent to your email.'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      if (isForgot) {
        // Forgot password flow
        const res = await fetch(`${API_URL}/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Error generating reset link.');
        setRequestSent(true);
        setMessage(isArabic
          ? 'إن كان البريد مسجلاً فقد أُرسل رمز الاستعادة. أدخله بالأسفل مع كلمة المرور الجديدة.'
          : 'If the email is registered, a reset token was sent. Enter it below with your new password.');
      } else if (isLogin) {
        // Login flow
        const res = await fetch(`${API_URL}/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (!res.ok) {
          if (res.status === 403 && String(data.detail || '').includes('EMAIL_NOT_VERIFIED')) {
            setIsVerify(true);
            setMessage(isArabic
              ? 'يرجى تأكيد بريدك الإلكتروني أولاً عبر الرمز المكوّن من 6 أرقام المرسل إلى بريدك.'
              : 'Please verify your email first using the 6-digit code sent to your inbox.');
            return;
          }
          throw new Error(data.detail || 'Login failed.');
        }
        
        localStorage.setItem('qto_token', data.token);
        localStorage.setItem('qto_user', JSON.stringify(data.user));
        onLoginSuccess(data.token, data.user);
      } else {
        // Register flow
        const res = await fetch(`${API_URL}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, name }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed.');
        
        if (data.requires_verification) {
          setIsVerify(true);
          setVerifyCode('');
          setMessage(isArabic
            ? 'تم إنشاء الحساب! أدخل رمز التأكيد المكوّن من 6 أرقام المرسل إلى بريدك الإلكتروني لتفعيله.'
            : 'Account created! Enter the 6-digit verification code sent to your email to activate.');
        } else {
          setMessage(isArabic ? 'تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.' : 'Registration successful! You can now log in.');
          setIsLogin(true);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Reset failed.');
      setMessage(isArabic ? 'تم تحديث كلمة المرور بنجاح.' : 'Password updated successfully.');
      setIsForgot(false);
      setIsLogin(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '12px',
      background: 'linear-gradient(135deg, var(--bg-primary), rgba(59, 130, 246, 0.05))',
    }}>
      <div className="glass-panel auth-panel" style={{
        width: '100%',
        maxWidth: '440px',
        padding: '40px 30px',
        textAlign: isArabic ? 'right' : 'left',
        direction: isArabic ? 'rtl' : 'ltr',
      }}>
        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '35px', justifyContent: 'center' }}>
          <img src={logo} alt="The QS Hub Logo" style={{ height: '45px', objectFit: 'contain' }} />
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 800 }}>THE QS HUB</h2>
        </div>

        <h3 style={{ marginBottom: '20px', fontSize: '1.3rem', fontWeight: 700 }}>
          {isVerify ? (isArabic ? 'تأكيد البريد الإلكتروني' : 'Verify Your Email') :
           isForgot ? (isArabic ? 'استعادة كلمة المرور' : 'Forgot Password') :
           isLogin ? (isArabic ? 'تسجيل الدخول للمنصة' : 'Sign In to Platform') :
           (isArabic ? 'إنشاء حساب جديد' : 'Create New Account')}
        </h3>

        {error && <div style={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          color: 'var(--error)',
          padding: '12px',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '0.9rem',
          borderLeft: isArabic ? 'none' : '4px solid var(--error)',
          borderRight: isArabic ? '4px solid var(--error)' : 'none',
        }}>{error}</div>}

        {message && <div style={{
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          color: 'var(--success)',
          padding: '12px',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '0.9rem',
          borderLeft: isArabic ? 'none' : '4px solid var(--success)',
          borderRight: isArabic ? '4px solid var(--success)' : 'none',
        }}>{message}</div>}

        {isVerify ? (
          <form onSubmit={handleVerifyEmail} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                {isArabic ? 'البريد الإلكتروني' : 'Email Address'}
              </label>
              <input
                type="email"
                className="form-input"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                {isArabic ? 'رمز التأكيد (6 أرقام)' : '6-Digit Verification Code'}
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                className="form-input"
                required
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456"
                style={{ letterSpacing: '6px', textAlign: 'center', fontSize: '1.25rem', fontWeight: 700 }}
              />
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading || verifyCode.length < 6}>
              {loading ? (isArabic ? 'جاري التحقق...' : 'Verifying...') : (isArabic ? 'تأكيد وتفعيل الحساب' : 'Verify & Activate Account')}
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleResendCode} disabled={loading} style={{ width: '100%' }}>
              {isArabic ? 'إعادة إرسال الرمز' : 'Resend Verification Code'}
            </button>
          </form>
        ) : !isForgot ? (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {!isLogin && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                  {isArabic ? 'الاسم الكامل' : 'Full Name'}
                </label>
                <input
                  type="text"
                  className="form-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={isArabic ? 'الاسم' : 'John Doe'}
                />
              </div>
            )}
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                {isArabic ? 'البريد الإلكتروني' : 'Email Address'}
              </label>
              <input
                type="email"
                className="form-input"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                {isArabic ? 'كلمة المرور' : 'Password'}
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? "text" : "password"}
                  className="form-input"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{ width: '100%', paddingRight: isArabic ? '10px' : '40px', paddingLeft: isArabic ? '40px' : '10px' }}
                />
                <div 
                  onClick={() => setShowPassword(!showPassword)}
                  style={{ 
                    position: 'absolute', 
                    top: '50%', 
                    transform: 'translateY(-50%)', 
                    [isArabic ? 'left' : 'right']: '10px', 
                    cursor: 'pointer', 
                    color: 'var(--text-muted)' 
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </div>
              </div>
            </div>

            {isLogin && (
              <div style={{ textAlign: isArabic ? 'left' : 'right' }}>
                <span 
                  onClick={() => setIsForgot(true)}
                  style={{ fontSize: '0.85rem', color: 'var(--primary)', cursor: 'pointer' }}
                >
                  {isArabic ? 'نسيت كلمة المرور؟' : 'Forgot Password?'}
                </span>
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }} disabled={loading}>
              {loading ? (isArabic ? 'جاري التحميل...' : 'Loading...') :
               isForgot ? (isArabic ? 'استعادة كلمة المرور' : 'Reset Password') :
               isLogin ? (isArabic ? 'دخول' : 'Sign In') :
               (isArabic ? 'إنشاء الحساب' : 'Sign Up')}
            </button>
          </form>
        ) : (
          <form onSubmit={requestSent ? handleResetPassword : handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            {!requestSent ? (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                  {isArabic ? 'أدخل البريد الإلكتروني للمطابقة' : 'Enter Registered Email'}
                </label>
                <input
                  type="email"
                  className="form-input"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                />
              </div>
            ) : (
              <>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                    {isArabic ? 'رمز الاستعادة' : 'Reset Token'}
                  </label>
                  <input
                    type="text"
                    className="form-input"
                    required
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="Reset token"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 500 }}>
                    {isArabic ? 'كلمة المرور الجديدة' : 'New Password'}
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showPassword ? "text" : "password"}
                      className="form-input"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      style={{ width: '100%', paddingRight: isArabic ? '10px' : '40px', paddingLeft: isArabic ? '40px' : '10px' }}
                    />
                    <div 
                      onClick={() => setShowPassword(!showPassword)}
                      style={{ 
                        position: 'absolute', 
                        top: '50%', 
                        transform: 'translateY(-50%)', 
                        [isArabic ? 'left' : 'right']: '10px', 
                        cursor: 'pointer', 
                        color: 'var(--text-muted)' 
                      }}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </div>
                  </div>
                </div>
              </>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }} disabled={loading}>
              {loading ? (isArabic ? 'جاري الإرسال...' : 'Sending...') :
               requestSent ? (isArabic ? 'تحديث كلمة المرور' : 'Update Password') :
               (isArabic ? 'طلب رمز الاستعادة' : 'Request Reset Token')}
            </button>
          </form>
        )}

        <div style={{ marginTop: '25px', textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          {isVerify ? (
            <span onClick={() => { setIsVerify(false); setIsLogin(true); setError(''); setMessage(''); }} style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: 600 }}>
              {isArabic ? 'العودة لتسجيل الدخول' : 'Back to Sign In'}
            </span>
          ) : isForgot ? (
            <span onClick={() => { setIsForgot(false); setRequestSent(false); setError(''); setMessage(''); }} style={{ color: 'var(--primary)', cursor: 'pointer' }}>
              {isArabic ? 'العودة لتسجيل الدخول' : 'Back to Login'}
            </span>
          ) : isLogin ? (
            <>
              {isArabic ? 'ليس لديك حساب؟ ' : "Don't have an account? "}
              <span onClick={() => { setIsLogin(false); setError(''); setMessage(''); }} style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: 600 }}>
                {isArabic ? 'سجل الآن' : 'Sign Up'}
              </span>
            </>
          ) : (
            <>
              {isArabic ? 'لديك حساب بالفعل؟ ' : 'Already have an account? '}
              <span onClick={() => { setIsLogin(true); setError(''); setMessage(''); }} style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: 600 }}>
                {isArabic ? 'تسجيل دخول' : 'Sign In'}
              </span>
            </>
          )}
        </div>

        {!isForgot && !isVerify && (
          <div style={{ marginTop: '30px' }}>
            <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0' }}>
              <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-color)' }}></div>
              <span style={{ padding: '0 15px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {isArabic ? 'أو الدخول عبر' : 'Or continue with'}
              </span>
              <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-color)' }}></div>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button className="btn" disabled style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', backgroundColor: 'white', color: '#999', border: '1px solid #ddd', cursor: 'not-allowed', opacity: 0.7, position: 'relative' }}>
                <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"/><path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"/><path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"/><path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"/></svg>
                {isArabic ? 'دخول بحساب Google' : 'Sign in with Google'}
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', backgroundColor: 'var(--primary)', padding: '2px 8px', borderRadius: '10px', marginLeft: isArabic ? '0' : '4px', marginRight: isArabic ? '4px' : '0' }}>
                  {isArabic ? 'قريباً' : 'Coming Soon'}
                </span>
              </button>
              <button className="btn" disabled style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', backgroundColor: 'white', color: '#999', border: '1px solid #ddd', cursor: 'not-allowed', opacity: 0.7, position: 'relative' }}>
                <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21"><path fill="#f25022" d="M1 1h9v9H1z"/><path fill="#00a4ef" d="M1 11h9v9H1z"/><path fill="#7fba00" d="M11 1h9v9h-9z"/><path fill="#ffb900" d="M11 11h9v9h-9z"/></svg>
                {isArabic ? 'دخول بحساب Microsoft' : 'Sign in with Microsoft'}
                <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#fff', backgroundColor: 'var(--primary)', padding: '2px 8px', borderRadius: '10px', marginLeft: isArabic ? '0' : '4px', marginRight: isArabic ? '4px' : '0' }}>
                  {isArabic ? 'قريباً' : 'Coming Soon'}
                </span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
