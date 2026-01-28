import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export interface User {
  id: number;
  email: string;
  name: string | null;
  created_at: string;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface RegisterResponse {
  message: string;
  user: User;
}

export const login = async (email: string, password: string): Promise<LoginResponse> => {
  const response = await axios.post(`${API_URL}/api/auth/login`, {
    email,
    password,
  });
  return response.data;
};

export const register = async (
  email: string,
  password: string,
  name?: string
): Promise<RegisterResponse> => {
  const response = await axios.post(`${API_URL}/api/auth/register`, {
    email,
    password,
    name,
  });
  return response.data;
};

export const getCurrentUser = async (): Promise<{ user: User }> => {
  const token = localStorage.getItem('access_token');
  const response = await axios.get(`${API_URL}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};

export const refreshToken = async (refresh_token: string): Promise<{ access_token: string }> => {
  const response = await axios.post(`${API_URL}/api/auth/refresh`, {
    refresh_token,
  });
  return response.data;
};

export const saveTokens = (accessToken: string, refreshToken: string) => {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
};

export const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
};

export const getStoredToken = () => {
  return localStorage.getItem('access_token');
};
