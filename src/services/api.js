// api.js

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { DeviceEventEmitter } from 'react-native';

const baseURL = process.env.EXPO_PUBLIC_BACKEND_URL || 'https://13-61-230-140.sslip.io';
console.log('[API] Current baseURL is:', baseURL);

const api = axios.create({
  baseURL,
});

api.interceptors.request.use(
  async config => {
    const token = await AsyncStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;

    if (
      !error.response ||
      error.response.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes('/auth/signin') ||
      originalRequest.url?.includes('/auth/signup') ||
      originalRequest.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        })
        .catch(err => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const storedRefreshToken = await AsyncStorage.getItem('refresh_token');
      if (!storedRefreshToken) {
        throw new Error('No refresh token stored');
      }

      // Use raw unintercepted axios to avoid recursive loops
      const refreshResponse = await axios.post(`${baseURL}/auth/refresh`, {
        refresh_token: storedRefreshToken,
      });

      const newAccessToken = refreshResponse.data?.access_token;
      if (!newAccessToken) {
        throw new Error('No access token returned from refresh');
      }

      await AsyncStorage.setItem('access_token', newAccessToken);
      api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;
      originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;

      processQueue(null, newAccessToken);

      // Trigger automatic re-render in UI components
      DeviceEventEmitter.emit('REFRESH_ALIGNED_DATA');
      DeviceEventEmitter.emit('REFRESH_MAP_DATA');

      return api(originalRequest);
    } catch (refreshErr) {
      processQueue(refreshErr, null);
      if (refreshErr.response?.status === 401 || refreshErr.response?.status === 400) {
        delete api.defaults.headers.common['Authorization'];
        await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        DeviceEventEmitter.emit('AUTH_LOGOUT');
      }
      return Promise.reject(refreshErr);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;