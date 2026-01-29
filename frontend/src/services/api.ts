import axios from 'axios';

// In Docker: nginx proxies /api/ to backend, so use empty string
// In local dev: use http://localhost:5001
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:5001';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses (token expired)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/api/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newToken = response.data.access_token;
          localStorage.setItem('access_token', newToken);

          // Retry original request
          error.config.headers.Authorization = `Bearer ${newToken}`;
          return api.request(error.config);
        } catch {
          // Refresh failed, clear tokens
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// API functions
export const askQuestion = async (question: string) => {
  const response = await api.post('/api/ask', { question });
  return response.data;
};

export const askAgent = async (question: string) => {
  const response = await api.post('/api/agent', { question });
  return response.data;
};

export const getSalesSummary = async () => {
  const response = await api.get('/api/sales/summary');
  return response.data;
};

export const getProducts = async () => {
  const response = await api.get('/api/products');
  return response.data;
};

export const getSchema = async () => {
  const response = await api.get('/api/schema');
  return response.data;
};

export const getCacheStats = async () => {
  const response = await api.get('/api/stats/cache');
  return response.data;
};

export const getRateLimitStatus = async () => {
  const response = await api.get('/api/stats/rate-limit');
  return response.data;
};

export const getQueryHistory = async (limit: number = 50) => {
  const response = await api.get(`/api/history?limit=${limit}`);
  return response.data;
};

export const getSessions = async () => {
  const response = await api.get('/api/sessions');
  return response.data;
};

export const createSession = async () => {
  const response = await api.post('/api/sessions');
  return response.data;
};

export const getSessionMessages = async (sessionId: number) => {
  const response = await api.get(`/api/sessions/${sessionId}`);
  return response.data;
};

export const updateSessionTitle = async (sessionId: number, title: string) => {
  const response = await api.put(`/api/sessions/${sessionId}`, { title });
  return response.data;
};

export const askQuestionInSession = async (question: string, sessionId: number) => {
  const response = await api.post('/api/ask', { question, session_id: sessionId });
  return response.data;
};

export const askAgentInSession = async (question: string, sessionId: number) => {
  const response = await api.post('/api/agent', { question, session_id: sessionId });
  return response.data;
};

export default api;
