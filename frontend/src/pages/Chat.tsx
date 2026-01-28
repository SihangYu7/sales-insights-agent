import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { askQuestion, askAgent } from '../services/api';

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

const Chat = () => {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [agentMode, setAgentMode] = useState<'simple' | 'advanced'>('advanced');
  const [showDetails, setShowDetails] = useState<number | null>(null);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

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
        ? await askAgent(input)
        : await askQuestion(input);

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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <Link to="/dashboard" className="text-gray-500 hover:text-gray-700">
              ← Dashboard
            </Link>
            <h1 className="text-2xl font-bold text-gray-900">AI Sales Assistant</h1>
          </div>
          <div className="flex items-center space-x-4">
            {/* Agent Mode Toggle */}
            <div className="flex items-center space-x-2 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setAgentMode('simple')}
                className={`px-3 py-1 rounded-md text-sm transition ${
                  agentMode === 'simple'
                    ? 'bg-white shadow text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Simple (SQL)
              </button>
              <button
                onClick={() => setAgentMode('advanced')}
                className={`px-3 py-1 rounded-md text-sm transition ${
                  agentMode === 'advanced'
                    ? 'bg-white shadow text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Advanced (Tools)
              </button>
            </div>
            <span className="text-gray-600">{user?.email}</span>
            <button onClick={logout} className="text-gray-500 hover:text-gray-700">
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <main className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <h2 className="text-xl font-semibold text-gray-700 mb-2">
                Ask me anything about your sales data!
              </h2>
              <p className="text-gray-500 mb-6">Try questions like:</p>
              <div className="flex flex-wrap justify-center gap-2">
                {[
                  'What are the total sales?',
                  'Top 3 products by revenue',
                  'Compare North vs South region sales',
                  'Average transaction value?',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="bg-white border border-gray-300 rounded-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white shadow border border-gray-200'
                }`}
              >
                <p className={message.role === 'user' ? 'text-white' : 'text-gray-900'}>
                  {message.content}
                </p>

                {/* Assistant message details */}
                {message.role === 'assistant' && (message.sql || message.tools_used) && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <button
                      onClick={() => setShowDetails(showDetails === message.id ? null : message.id)}
                      className="text-sm text-blue-600 hover:text-blue-700"
                    >
                      {showDetails === message.id ? 'Hide details' : 'Show details'}
                    </button>

                    {showDetails === message.id && (
                      <div className="mt-2 space-y-2 text-sm">
                        {message.cache_hit !== undefined && (
                          <div className="flex items-center space-x-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              message.cache_hit
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}>
                              {message.cache_hit ? 'Cache Hit' : 'Cache Miss'}
                            </span>
                          </div>
                        )}

                        {message.tools_used && message.tools_used.length > 0 && (
                          <div>
                            <span className="text-gray-500">Tools used: </span>
                            <span className="text-gray-700">{message.tools_used.join(', ')}</span>
                          </div>
                        )}

                        {message.sql && (
                          <div>
                            <span className="text-gray-500">SQL: </span>
                            <code className="bg-gray-100 px-2 py-1 rounded text-xs block mt-1 overflow-x-auto">
                              {message.sql}
                            </code>
                          </div>
                        )}

                        {message.metrics && (
                          <div className="flex flex-wrap gap-2 mt-2">
                            {message.metrics.total_duration_seconds && (
                              <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">
                                {message.metrics.total_duration_seconds.toFixed(2)}s
                              </span>
                            )}
                            {message.metrics.estimated_cost_usd && (
                              <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">
                                ${message.metrics.estimated_cost_usd.toFixed(5)}
                              </span>
                            )}
                            {message.metrics.total_input_tokens && (
                              <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">
                                {message.metrics.total_input_tokens} in / {message.metrics.total_output_tokens} out
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
              <div className="bg-white shadow border border-gray-200 rounded-lg p-4">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white p-4">
        <div className="max-w-4xl mx-auto flex space-x-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your sales data..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading || !input.trim()}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-500 mt-2">
          Using {agentMode === 'advanced' ? 'Advanced Agent (Module 5)' : 'Simple SQL Agent (Module 4)'}
        </p>
      </div>
    </div>
  );
};

export default Chat;
