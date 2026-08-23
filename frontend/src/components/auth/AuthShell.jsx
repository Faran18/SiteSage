import { Bot } from 'lucide-react';

export default function AuthShell({ children }) {
  return (
    <div className="min-h-screen w-full bg-gray-950 relative overflow-hidden">
      {/* Soft blobs */}
      <div className="absolute -top-40 -left-40 w-[520px] h-[520px] rounded-full bg-primary-600/30 blur-3xl" />
      <div className="absolute -bottom-40 -right-40 w-[520px] h-[520px] rounded-full bg-secondary-600/30 blur-3xl" />

      {/* Subtle grid */}
      <div
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage:
            'linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <div className="relative z-10 min-h-screen flex items-center justify-center px-4 py-10">
        <div className="w-full max-w-5xl">
          {/* Brand */}
          <div className="flex items-center justify-center mb-8">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-2xl flex items-center justify-center shadow-xl">
                <Bot className="w-7 h-7 text-white" />
              </div>
              <div>
                <div className="text-white text-xl font-bold leading-tight">SiteSage</div>
                <div className="text-gray-300 text-sm">Sign in to continue</div>
              </div>
            </div>
          </div>

          {children}

          <div className="text-center mt-8 text-gray-400 text-xs">
            © 2024 AI Agent Hub
          </div>
        </div>
      </div>
    </div>
  );
}
