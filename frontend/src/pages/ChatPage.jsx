import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, ArrowLeft, Bot, User, Loader2, Plus, Link as LinkIcon } from 'lucide-react';
import toast from 'react-hot-toast';
import { agentService } from '../services/agentService';

export default function ChatPage() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const [agent, setAgent] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingAgent, setLoadingAgent] = useState(true);
  const [showAddUrl, setShowAddUrl] = useState(false);
  const [newUrl, setNewUrl] = useState('');
  const [scraping, setScraping] = useState(false);
  const [multiPage, setMultiPage] = useState(false);
  const [maxPages, setMaxPages] = useState(25);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchAgent();
  }, [agentId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchAgent = async () => {
    try {
      setLoadingAgent(true);
      const response = await agentService.getAgent(agentId);
      setAgent(response.agent);
      
      // Check if agent has any scrape configs
      if (!response.scrape_configs || response.scrape_configs.length === 0) {
        setShowAddUrl(true);
      }
    } catch (error) {
      toast.error('Failed to load agent');
      navigate('/agents');
    } finally {
      setLoadingAgent(false);
    }
  };

  const handleAddUrl = async (e) => {
    e.preventDefault();
    
    if (!newUrl.trim()) return;

    try {
      setScraping(true);
      toast.loading('Scraping website...', { id: 'scrape' });
      
      await agentService.scrapeUrl(agentId, newUrl.trim(), {
        auto_scrape: false,
        multi_page: multiPage,
        max_pages: maxPages,
      });
      
      toast.success('Website scraped successfully!', { id: 'scrape' });
      setNewUrl('');
      setShowAddUrl(false);
      fetchAgent();
    } catch (error) {
      toast.error('Failed to scrape website', { id: 'scrape' });
      console.error(error);
    } finally {
      setScraping(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!input.trim() || loading) return;

    const userMessage = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await agentService.chat(agentId, userMessage.content);
      
      const assistantMessage = {
        role: 'assistant',
        content: response.message,
        source_url: response.source_url,
        chunks_used: response.chunks_used,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      toast.error('Failed to get response');
      console.error(error);
      
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  if (loadingAgent) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  if (!agent) {
    return null;
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-t-xl shadow-lg p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={() => navigate('/agents')}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>Back to Agents</span>
          </button>
          
          <button
            onClick={() => setShowAddUrl(!showAddUrl)}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-50 text-primary-600 rounded-lg hover:bg-primary-100 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add URL</span>
          </button>
        </div>

        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-xl flex items-center justify-center flex-shrink-0">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{agent.name}</h1>
            <p className="text-gray-600">{agent.role}</p>
          </div>
        </div>

        {/* Add URL Form */}
        {showAddUrl && (
          <form onSubmit={handleAddUrl} className="mt-4 p-4 bg-gray-50 rounded-lg">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Add URL to Knowledge Base
            </label>
            <div className="flex space-x-2">
              <input
                type="url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://example.com"
                required
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <button
                type="submit"
                disabled={scraping || !newUrl.trim()}
                className="px-6 py-2 bg-primary-500 text-white rounded-lg font-semibold hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {scraping ? 'Scraping...' : 'Add'}
              </button>
            </div>
            <label className="flex items-center mt-3 text-sm text-gray-600 space-x-2">
              <input
                type="checkbox"
                checked={multiPage}
                onChange={(e) => setMultiPage(e.target.checked)}
                className="rounded border-gray-300 text-primary-500 focus:ring-primary-500"
              />
              <span>Crawl multiple pages (follow pagination and subcategories on this site)</span>
            </label>
            {multiPage && (
              <label className="flex items-center mt-2 ml-6 text-sm text-gray-600 space-x-2">
                <span>Max pages to crawl:</span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  className="w-20 px-2 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </label>
            )}
          </form>
        )}
      </div>

      {/* Chat Messages */}
      <div className="bg-white shadow-lg" style={{ height: 'calc(100vh - 400px)', minHeight: '400px' }}>
        <div className="h-full overflow-y-auto p-6 space-y-4 custom-scrollbar">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
              <Bot className="w-16 h-16 text-gray-300" />
              <div>
                <h3 className="text-lg font-semibold text-gray-700">
                  Start a conversation
                </h3>
                <p className="text-gray-500">
                  Ask me anything about the content I've learned
                </p>
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-3xl flex space-x-3 ${
                    message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                  }`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      message.role === 'user'
                        ? 'bg-gray-200'
                        : 'bg-gradient-to-br from-primary-500 to-secondary-500'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <User className="w-6 h-6 text-gray-600" />
                    ) : (
                      <Bot className="w-6 h-6 text-white" />
                    )}
                  </div>

                  {/* Message Content */}
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    
                    {message.source_url && (
                      <a
                        href={message.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary-300 hover:text-white flex items-center space-x-1 mt-2"
                      >
                        <LinkIcon className="w-3 h-3" />
                        <span>Source</span>
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          
          {loading && (
            <div className="flex justify-start">
              <div className="max-w-3xl flex space-x-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary-500 to-secondary-500 flex items-center justify-center">
                  <Bot className="w-6 h-6 text-white" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-gray-100">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-600" />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Form */}
      <form
        onSubmit={handleSendMessage}
        className="bg-white rounded-b-xl shadow-lg p-4 border-t border-gray-200"
      >
        <div className="flex space-x-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything..."
            disabled={loading}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-gradient-to-r from-primary-500 to-secondary-500 text-white rounded-lg font-semibold hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Send className="w-5 h-5" />
            <span>Send</span>
          </button>
        </div>
      </form>
    </div>
  );
}