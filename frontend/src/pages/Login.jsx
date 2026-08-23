import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import ForgotPasswordModal from '../components/auth/ForgotPasswordModal';
import { useAuth } from '../context/AuthContext';
import { getApiErrorMessage } from '../utils/httpError';

export default function Login() {
  const navigate = useNavigate();
  const { login, signup } = useAuth();

  const [isSignUp, setIsSignUp] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);

  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) navigate('/');
  }, [navigate]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail.trim() || !loginPassword.trim()) return;

    setLoading(true);
    try {
      await login(loginEmail.trim(), loginPassword.trim());
      toast.success('Login successful');
      navigate('/');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Login failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (!signupName.trim() || !signupEmail.trim() || !signupPassword.trim()) return;

    const payload = {
      email: signupEmail.trim(),
      password: signupPassword.trim(),
      full_name: signupName.trim(),
    };

    console.log('SIGNUP PAYLOAD:', payload);

    setLoading(true);
    try {
      await signup(payload.email, payload.password, payload.full_name);
      toast.success('Account created');
      navigate('/');
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Signup failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#eef1f7] flex items-center justify-center px-4">
      <div className="relative w-full max-w-4xl">
        <div className="relative bg-white rounded-2xl shadow-2xl overflow-hidden h-[520px] transition-all duration-700">
          <div className="absolute inset-0">
            {/* Sign In */}
            <div
              className={`absolute top-0 left-0 w-1/2 h-full flex items-center justify-center p-10 transition-all duration-700
              ${isSignUp ? 'opacity-0 pointer-events-none -translate-x-6' : 'opacity-100 translate-x-0'}`}
            >
              <form onSubmit={handleLogin} className="w-full max-w-sm">
                <h2 className="text-3xl font-bold text-gray-900 text-center">Sign In</h2>
                <p className="text-gray-500 text-sm text-center mt-2">Or use your email account</p>

                <div className="mt-8 space-y-4">
                  <input
                    id="login_email"
                    name="email"
                    autoComplete="email"
                    type="email"
                    placeholder="Email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg bg-gray-100 border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:bg-white outline-none"
                    required
                  />
                  <input
                    id="login_password"
                    name="password"
                    autoComplete="current-password"
                    type="password"
                    placeholder="Password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg bg-gray-100 border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:bg-white outline-none"
                    required
                  />
                </div>

                <div className="mt-4 flex justify-center">
                  <button
                    type="button"
                    onClick={() => setForgotOpen(true)}
                    className="text-sm text-gray-500 hover:text-gray-800"
                  >
                    Forgot password?
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="mt-6 w-full py-3 rounded-full font-semibold text-white bg-gradient-to-r from-primary-500 to-secondary-500 hover:shadow-lg transition disabled:opacity-50"
                >
                  {loading ? 'Signing in...' : 'SIGN IN'}
                </button>
              </form>
            </div>

            {/* Sign Up */}
            <div
              className={`absolute top-0 right-0 w-1/2 h-full flex items-center justify-center p-10 transition-all duration-700
              ${isSignUp ? 'opacity-100 translate-x-0' : 'opacity-0 pointer-events-none translate-x-6'}`}
            >
              <form onSubmit={handleSignup} className="w-full max-w-sm">
                <h2 className="text-3xl font-bold text-gray-900 text-center">Create Account</h2>
                <p className="text-gray-500 text-sm text-center mt-2">Use your email for registration</p>

                <div className="mt-8 space-y-4">
                  <input
                    id="signup_full_name"
                    name="full_name"
                    autoComplete="name"
                    type="text"
                    placeholder="Full name"
                    value={signupName}
                    onChange={(e) => setSignupName(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg bg-gray-100 border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:bg-white outline-none"
                    required
                  />
                  <input
                    id="signup_email"
                    name="email"
                    autoComplete="email"
                    type="email"
                    placeholder="Email"
                    value={signupEmail}
                    onChange={(e) => setSignupEmail(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg bg-gray-100 border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:bg-white outline-none"
                    required
                  />
                  <input
                    id="signup_password"
                    name="password"
                    autoComplete="new-password"
                    type="password"
                    placeholder="Password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    className="w-full px-4 py-3 rounded-lg bg-gray-100 border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:bg-white outline-none"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="mt-6 w-full py-3 rounded-full font-semibold text-white bg-gradient-to-r from-primary-500 to-secondary-500 hover:shadow-lg transition disabled:opacity-50"
                >
                  {loading ? 'Signing up...' : 'SIGN UP'}
                </button>
              </form>
            </div>
          </div>

          {/* Sliding blue panel */}
          <div
            className={`absolute top-0 h-full w-1/2 bg-[#3b57d6] transition-all duration-700 ease-in-out
            ${isSignUp ? 'left-0 rounded-r-2xl' : 'left-1/2 rounded-l-2xl'}`}
          >
            <div className="h-full flex flex-col items-center justify-center text-center px-10 text-white">
              {!isSignUp ? (
                <>
                  <h2 className="text-3xl font-bold">Hey There!</h2>
                  <p className="mt-3 text-white/80">Begin your automation journey using SiteSage, and start scraping now.</p>
                  <button
                    onClick={() => setIsSignUp(true)}
                    className="mt-6 px-10 py-3 rounded-full border-2 border-white font-semibold hover:bg-white hover:text-[#3b57d6] transition"
                  >
                    SIGN UP
                  </button>
                </>
              ) : (
                <>
                  <h2 className="text-3xl font-bold">Welcome Back!</h2>
                  <p className="mt-3 text-white/80">To keep connected with us please login with your personal info.</p>
                  <button
                    onClick={() => setIsSignUp(false)}
                    className="mt-6 px-10 py-3 rounded-full border-2 border-white font-semibold hover:bg-white hover:text-[#3b57d6] transition"
                  >
                    SIGN IN
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <ForgotPasswordModal isOpen={forgotOpen} onClose={() => setForgotOpen(false)} />
    </div>
  );
}
