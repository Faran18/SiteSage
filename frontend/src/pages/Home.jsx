import { Link } from 'react-router-dom';
import { Bot, Bell, Zap, Shield, Clock, MessageSquare } from 'lucide-react';
import HeroSection from '../components/home/HeroSection';

export default function Home() {
  const features = [
    {
      icon: Bot,
      title: 'AI Agents',
      description: 'Create intelligent agents that learn from any website',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: Bell,
      title: 'Smart Reminders',
      description: 'Get notified when website content changes',
      color: 'from-purple-500 to-pink-500',
    },
    {
      icon: MessageSquare,
      title: 'Interactive Chat',
      description: 'Chat with your agents using natural language',
      color: 'from-green-500 to-emerald-500',
    },
    {
      icon: Clock,
      title: 'Auto Monitoring',
      description: 'Scheduled scraping with customizable intervals',
      color: 'from-orange-500 to-red-500',
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Powered by Playwright for reliable web scraping',
      color: 'from-yellow-500 to-amber-500',
    },
    {
      icon: Shield,
      title: 'Secure & Private',
      description: 'Your data stays safe with local LLM processing',
      color: 'from-indigo-500 to-purple-500',
    },
  ];

  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center space-y-8 py-12">
        <div className="animate-fade-in">
          <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-primary-600 via-secondary-600 to-primary-600 bg-clip-text text-transparent mb-4">
            SiteSage: Your Web Agent Hub
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Transform any website into an intelligent agent. Monitor changes, chat with content, and automate your workflow.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center animate-slide-up">
          <Link
            to="/agents"
            className="px-8 py-4 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-xl font-semibold hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex items-center space-x-2"
          >
            <Bot className="w-5 h-5" />
            <span>Create Your First Agent</span>
          </Link>
          <Link
            to="/reminders"
            className="px-8 py-4 bg-white text-gray-700 border-2 border-gray-300 rounded-xl font-semibold hover:border-primary-500 hover:text-primary-600 transition-all duration-300 flex items-center space-x-2"
          >
            <Bell className="w-5 h-5" />
            <span>Set Up Reminders</span>
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-12">
        <h2 className="text-3xl font-bold text-center mb-12">
          Powerful Features
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <div
                key={index}
                className="bg-white p-6 rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 card-hover"
              >
                <div className={`w-14 h-14 bg-gradient-to-br ${feature.color} rounded-xl flex items-center justify-center mb-4`}>
                  <Icon className="w-8 h-8 text-white" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-gradient-to-br from-primary-50 to-secondary-50 rounded-3xl p-12">
        <h2 className="text-3xl font-bold text-center mb-12">
          How It Works
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-primary-500 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
              1
            </div>
            <h3 className="text-xl font-semibold">Create Agent</h3>
            <p className="text-gray-600">
              Give your agent a name and role, then add URLs to scrape
            </p>
          </div>
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-secondary-500 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
              2
            </div>
            <h3 className="text-xl font-semibold">Chat & Monitor</h3>
            <p className="text-gray-600">
              Interact with your agent and set up automatic monitoring
            </p>
          </div>
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-primary-500 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
              3
            </div>
            <h3 className="text-xl font-semibold">Get Notified</h3>
            <p className="text-gray-600">
              Receive email alerts when content changes are detected
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}