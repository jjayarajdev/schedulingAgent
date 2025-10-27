import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface Project {
  id: string;
  number: string;
  type: string;
  category: string;
  status: string;
  address: string;
  scheduled_date?: string;
  scheduled_time?: string;
  technician: string;
  store: string;
}

interface User {
  customer_id: string;
  customer_type: string;
  name: string;
  email: string;
  projects: Project[];
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

const SAMPLE_QUERIES = [
  "Show me all my projects",
  "What dates are available for project 12347?",
  "Tell me about project 12345",
  "What are your business hours?",
  "Add a note to project 12345: Customer prefers morning appointments"
];

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your property management assistant. How can I help you today?',
      timestamp: Date.now()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load user data
    axios.get('/api/user')
      .then(response => setUser(response.data))
      .catch(error => console.error('Error loading user:', error));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: text,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('/api/chat/simple', {
        message: text
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: Date.now()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, errorMessage]);
      console.error('Error sending message:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const getStatusColor = (status: string) => {
    return status === 'Scheduled' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Property Management Portal</h1>
              <p className="text-sm text-gray-600">Powered by AWS Bedrock Multi-Agent System</p>
            </div>
            {user && (
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900">{user.name}</p>
                <p className="text-xs text-gray-600">ID: {user.customer_id} • {user.customer_type}</p>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Column - Projects */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">My Projects</h2>
              <div className="space-y-4">
                {user?.projects.map((project) => (
                  <div
                    key={project.id}
                    className={`border rounded-lg p-4 cursor-pointer transition ${
                      selectedProject?.id === project.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedProject(project)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-gray-900">{project.category}</h3>
                        <p className="text-xs text-gray-600">{project.number}</p>
                      </div>
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(project.status)}`}>
                        {project.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{project.address}</p>
                    {project.scheduled_date && (
                      <div className="text-xs text-gray-600">
                        <p>📅 {project.scheduled_date}</p>
                        <p>🕐 {project.scheduled_time}</p>
                      </div>
                    )}
                    <p className="text-xs text-gray-600 mt-2">👤 {project.technician}</p>
                  </div>
                ))}
              </div>

              {/* Sample Queries */}
              <div className="mt-6 pt-6 border-t border-gray-200">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Quick Actions</h3>
                <div className="space-y-2">
                  {SAMPLE_QUERIES.map((query, index) => (
                    <button
                      key={index}
                      onClick={() => sendMessage(query)}
                      disabled={loading}
                      className="w-full text-left text-xs px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded border border-gray-200 transition disabled:opacity-50"
                    >
                      {query}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Chat */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow flex flex-col h-[calc(100vh-12rem)]">
              {/* Chat Header */}
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">AI Assistant</h2>
                <p className="text-sm text-gray-600">
                  Multi-agent system: Scheduling • Information • Notes • Chitchat
                </p>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-lg px-4 py-3 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-900'
                      }`}
                    >
                      <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      <p className={`text-xs mt-1 ${
                        message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                      }`}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg px-4 py-3">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="px-6 py-4 border-t border-gray-200">
                <form onSubmit={handleSubmit} className="flex space-x-4">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about your projects, schedule appointments, check availability..."
                    disabled={loading}
                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition"
                  >
                    {loading ? 'Sending...' : 'Send'}
                  </button>
                </form>
                <p className="text-xs text-gray-500 mt-2">
                  💡 Tip: Ask about your projects, availability, or request scheduling
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-600">
          <p>
            Using mock data (CUST001) • Projects: 12345 (Flooring), 12347 (Windows), 12350 (Deck Repair)
          </p>
          <p className="text-xs mt-1">
            Backend: AWS Bedrock • Model: Claude Sonnet 4.5 • Architecture: Supervisor + 4 Specialists
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;
