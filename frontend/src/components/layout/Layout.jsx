// frontend/src/components/layout/Layout.jsx
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { Home, Bot, Bell, Menu, X, LogIn, LogOut, Trash2, User2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '../../context/AuthContext';

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { user, isAuthed, logout, deleteAccount } = useAuth();

  // ✅ Hide navbar/footer on login page (cleaner)
  const isAuthScreen = location.pathname === '/login';

  const navigation = useMemo(
    () => [
      { name: 'Home', href: '/', icon: Home, public: true, match: (p) => p === '/' },
      { name: 'My Agents', href: '/agents', icon: Bot, public: false, match: (p) => p.startsWith('/agents') },
      { name: 'Reminders', href: '/reminders', icon: Bell, public: false, match: (p) => p.startsWith('/reminders') },
    ],
    []
  );

  const visibleNav = useMemo(() => navigation.filter((n) => n.public || isAuthed), [navigation, isAuthed]);

  const isActive = (itemHref) => {
    const item = navigation.find((n) => n.href === itemHref);
    if (!item) return false;
    return item.match(location.pathname);
  };

  const clearAuthAndGoLogin = () => {
    localStorage.removeItem('auth_token');
    setMobileMenuOpen(false);
    navigate('/login');
  };

  const onLogout = async () => {
    try {
      await logout();
    } catch (e) {
      // even if backend fails, remove local auth so UI doesn't get stuck
      console.error('Logout error:', e);
    }
    toast.success('Logged out');
    clearAuthAndGoLogin();
  };

  const onDelete = async () => {
    if (!confirm('Delete your account? This will deactivate your user.')) return;

    try {
      await deleteAccount();
      toast.success('Account deleted');
      clearAuthAndGoLogin();
    } catch (e) {
      console.error('Delete account error:', e);
      const msg =
        e?.response?.data?.detail ||
        e?.response?.data?.message ||
        e?.message ||
        'Failed to delete account';
      toast.error(msg);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      {!isAuthScreen && (
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="h-16 flex items-center justify-between">
              {/* Logo */}
              <Link to="/" className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center shadow-sm">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <span className="text-lg sm:text-xl font-bold bg-gradient-to-r from-primary-600 to-secondary-600 bg-clip-text text-transparent">
                  SiteSage
                </span>
              </Link>

              {/* Desktop nav */}
              <div className="hidden md:flex items-center gap-2">
                <div className="flex items-center gap-1">
                  {visibleNav.map((item) => {
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={`h-10 px-4 rounded-xl flex items-center gap-2 text-sm font-semibold transition-colors ${
                          isActive(item.href)
                            ? 'bg-primary-50 text-primary-700'
                            : 'text-gray-600 hover:bg-gray-100'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        <span>{item.name}</span>
                      </Link>
                    );
                  })}
                </div>

                {/* Right actions */}
                <div className="ml-4 pl-4 border-l border-gray-200 flex items-center gap-2">
                  {!isAuthed ? (
                    <Link
                      to="/login"
                      className="h-10 px-4 rounded-xl bg-gray-900 text-white hover:bg-gray-800 transition-colors flex items-center gap-2 text-sm font-semibold shadow-sm"
                    >
                      <LogIn className="w-4 h-4" />
                      <span>Login</span>
                    </Link>
                  ) : (
                    <>
                      <div className="h-10 px-3 rounded-xl bg-gray-100 text-gray-700 flex items-center gap-2 max-w-[260px]">
                        <User2 className="w-4 h-4" />
                        <span className="text-sm font-semibold truncate">
                          {user?.full_name || user?.email}
                        </span>
                      </div>

                      <button
                        onClick={onLogout}
                        className="h-10 px-4 rounded-xl bg-white border border-gray-200 hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-semibold"
                        type="button"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Logout</span>
                      </button>

                      <button
                        onClick={onDelete}
                        className="h-10 px-4 rounded-xl bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 transition-colors flex items-center gap-2 text-sm font-semibold"
                        title="Delete account"
                        type="button"
                      >
                        <Trash2 className="w-4 h-4" />
                        <span>Delete</span>
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Mobile button */}
              <div className="md:hidden">
                <button
                  onClick={() => setMobileMenuOpen((v) => !v)}
                  className="p-2 rounded-xl text-gray-600 hover:bg-gray-100"
                  type="button"
                >
                  {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                </button>
              </div>
            </div>
          </div>

          {/* Mobile nav */}
          {mobileMenuOpen && (
            <div className="md:hidden border-t border-gray-200 bg-white">
              <div className="px-3 py-3 space-y-1">
                {visibleNav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`h-11 px-4 rounded-xl flex items-center gap-2 text-sm font-semibold transition-colors ${
                        isActive(item.href)
                          ? 'bg-primary-50 text-primary-700'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}

                <div className="pt-2 mt-2 border-t border-gray-200 space-y-2">
                  {!isAuthed ? (
                    <Link
                      to="/login"
                      onClick={() => setMobileMenuOpen(false)}
                      className="h-11 px-4 rounded-xl bg-gray-900 text-white flex items-center gap-2 text-sm font-semibold"
                    >
                      <LogIn className="w-4 h-4" />
                      <span>Login</span>
                    </Link>
                  ) : (
                    <>
                      <div className="h-11 px-4 rounded-xl bg-gray-100 text-gray-700 flex items-center gap-2">
                        <User2 className="w-4 h-4" />
                        <span className="text-sm font-semibold truncate">
                          {user?.full_name || user?.email}
                        </span>
                      </div>

                      <button
                        onClick={onLogout}
                        className="w-full h-11 px-4 rounded-xl bg-white border border-gray-200 flex items-center gap-2 text-sm font-semibold"
                        type="button"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Logout</span>
                      </button>

                      <button
                        onClick={onDelete}
                        className="w-full h-11 px-4 rounded-xl bg-red-50 text-red-700 border border-red-200 flex items-center gap-2 text-sm font-semibold"
                        type="button"
                      >
                        <Trash2 className="w-4 h-4" />
                        <span>Delete account</span>
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </nav>
      )}

      {/* Content */}
      <main className={isAuthScreen ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
        <Outlet />
      </main>

      {/* Footer */}
      {!isAuthScreen && (
        <footer className="bg-white border-t border-gray-200 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <p className="text-center text-gray-500 text-sm">
              © 2026 SiteSage. Powered by FastAPI & React.
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}
