import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  getSessions,
  createSession,
  getSessionMessages,
  askQuestionInSession,
  askAgentInSession,
  updateSessionTitle
} from '../services/api';

interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  results?: unknown;
  tools_used?: string[];
  cache_hit?: boolean;
  metrics?: {
    total_duration_seconds?: number;
    estimated_cost_usd?: number;
    total_input_tokens?: number;
    total_output_tokens?: number;
  };
}

interface Session {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

const Chat = () => {
  const { user, logout } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [agentMode, setAgentMode] = useState<'simple' | 'advanced'>('advanced');
  const [showDetails, setShowDetails] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    }
  };

  const loadSession = async (sessionId: number) => {
    try {
      const data = await getSessionMessages(sessionId);
      setActiveSessionId(sessionId);

      // Convert history items to messages
      const loadedMessages: Message[] = [];
      for (const item of data.messages || []) {
        loadedMessages.push({
          id: item.id * 2,
          role: 'user',
          content: item.question,
        });
        loadedMessages.push({
          id: item.id * 2 + 1,
          role: 'assistant',
          content: item.answer,
          sql: item.sql_query,
        });
      }
      setMessages(loadedMessages);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const startNewChat = async () => {
    try {
      const session = await createSession();
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    // Create session if none active
    let sessionId = activeSessionId;
    if (!sessionId) {
      try {
        const session = await createSession();
        setSessions((prev) => [session, ...prev]);
        sessionId = session.id;
        setActiveSessionId(session.id);
      } catch (err) {
        console.error('Failed to create session:', err);
        return;
      }
    }

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = agentMode === 'advanced'
        ? await askAgentInSession(input, sessionId!)
        : await askQuestionInSession(input, sessionId!);

      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.answer,
        sql: response.sql,
        results: response.results,
        tools_used: response.tools_used,
        cache_hit: response.cache_hit,
        metrics: response.metrics,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Refresh sessions to update titles
      fetchSessions();
    } catch (err) {
      const errorMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const startEditingSession = (session: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditingTitle(session.title);
  };

  const saveSessionTitle = async () => {
    if (!editingSessionId || !editingTitle.trim()) {
      setEditingSessionId(null);
      return;
    }

    try {
      await updateSessionTitle(editingSessionId, editingTitle.trim());
      setSessions((prev) =>
        prev.map((s) =>
          s.id === editingSessionId ? { ...s, title: editingTitle.trim() } : s
        )
      );
    } catch (err) {
      console.error('Failed to update session title:', err);
    }
    setEditingSessionId(null);
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveSessionTitle();
    } else if (e.key === 'Escape') {
      setEditingSessionId(null);
    }
  };

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-gray-900 text-white flex flex-col transition-all duration-300 overflow-hidden`}>
        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 hover:bg-gray-800 transition text-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-2">
          {sessions.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No conversations yet</p>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => loadSession(session.id)}
                  className={`group w-full text-left px-3 py-2 rounded-lg text-sm transition cursor-pointer ${
                    activeSessionId === session.id
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-300 hover:bg-gray-800'
                  }`}
                >
                  {editingSessionId === session.id ? (
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onBlur={saveSessionTitle}
                      onKeyDown={handleEditKeyDown}
                      onClick={(e) => e.stopPropagation()}
                      className="w-full bg-gray-600 text-white px-1 py-0.5 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                      autoFocus
                    />
                  ) : (
                    <div className="flex items-center justify-between">
                      <div className="truncate flex-1">{session.title}</div>
                      <button
                        onClick={(e) => startEditingSession(session, e)}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-600 rounded transition"
                        title="Edit title"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                    </div>
                  )}
                  <div className="text-xs text-gray-500 mt-0.5">
                    {formatDate(session.updated_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* User Info */}
        <div className="p-3 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400 truncate">{user?.email}</span>
            <button
              onClick={logout}
              className="text-gray-500 hover:text-gray-300 text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <Link to="/dashboard" className="text-gray-500 hover:text-gray-700 text-sm">
              Dashboard
            </Link>
            <h1 className="text-lg font-semibold text-gray-900">AI Sales Assistant</h1>
          </div>

          {/* Agent Mode Toggle */}
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setAgentMode('simple')}
              className={`px-3 py-1 rounded-md text-sm transition ${
                agentMode === 'simple'
                  ? 'bg-white shadow text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Simple
            </button>
            <button
              onClick={() => setAgentMode('advanced')}
              className={`px-3 py-1 rounded-md text-sm transition ${
                agentMode === 'advanced'
                  ? 'bg-white shadow text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Advanced
            </button>
          </div>
        </header>

        {/* Messages Area */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto py-6 px-4">
            {messages.length === 0 ? (
              <div className="text-center py-16">
                <h2 className="text-2xl font-semibold text-gray-800 mb-3">
                  AI Sales Assistant
                </h2>
                <p className="text-gray-500 mb-8">Ask questions about your sales data</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    'What are the total sales?',
                    'Top 3 products by revenue',
                    'Sales by region',
                    'Average transaction value',
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => setInput(q)}
                      className="bg-white border border-gray-200 rounded-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-200 shadow-sm'
                      }`}
                    >
                      <p className={`whitespace-pre-wrap ${message.role === 'user' ? 'text-white' : 'text-gray-800'}`}>
                        {message.content}
                      </p>

                      {/* Details toggle for assistant messages */}
                      {message.role === 'assistant' && (message.sql || message.tools_used) && (
                        <div className="mt-3 pt-2 border-t border-gray-100">
                          <button
                            onClick={() => setShowDetails(showDetails === message.id ? null : message.id)}
                            className="text-xs text-blue-600 hover:text-blue-700"
                          >
                            {showDetails === message.id ? 'Hide details' : 'Show details'}
                          </button>

                          {showDetails === message.id && (
                            <div className="mt-2 space-y-2 text-sm">
                              {message.cache_hit !== undefined && (
                                <span className={`inline-block px-2 py-0.5 rounded text-xs ${
                                  message.cache_hit
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-gray-100 text-gray-600'
                                }`}>
                                  {message.cache_hit ? 'Cached' : 'Fresh'}
                                </span>
                              )}

                              {message.tools_used && message.tools_used.length > 0 && (
                                <div className="text-gray-600">
                                  <span className="text-gray-500">Tools: </span>
                                  {message.tools_used.join(', ')}
                                </div>
                              )}

                              {message.sql && (
                                <div>
                                  <span className="text-gray-500 text-xs">SQL:</span>
                                  <code className="block bg-gray-50 px-2 py-1.5 rounded text-xs mt-1 overflow-x-auto text-gray-700">
                                    {message.sql}
                                  </code>
                                </div>
                              )}

                              {message.metrics && (
                                <div className="flex flex-wrap gap-2">
                                  {message.metrics.total_duration_seconds && (
                                    <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs">
                                      {message.metrics.total_duration_seconds.toFixed(2)}s
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 shadow-sm rounded-2xl px-4 py-3">
                      <div className="flex space-x-1.5">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </main>

        {/* Input Area */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your sales data..."
                className="w-full border border-gray-300 rounded-xl px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={isLoading || !input.trim()}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-blue-600 hover:bg-blue-50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                </svg>
              </button>
            </div>
            <p className="text-center text-xs text-gray-400 mt-2">
              {agentMode === 'advanced' ? 'Advanced mode with tools' : 'Simple SQL mode'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Chat;
