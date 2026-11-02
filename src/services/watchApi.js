import api from './api';

export const getWatchSessions = async () => {
  const response = await api.get('/watch');
  return response.data;
};

export const createWatchSession = async (data) => {
  const response = await api.post('/watch', data);
  return response.data;
};

export const getWatchSession = async (sessionId) => {
  const response = await api.get(`/watch/${sessionId}`);
  return response.data;
};

export const updateWatchSession = async (sessionId, data) => {
  const response = await api.put(`/watch/${sessionId}`, data);
  return response.data;
};

export const deleteWatchSession = async (sessionId) => {
  const response = await api.delete(`/watch/${sessionId}`);
  return response.data;
};

export const acceptWatchSession = async (sessionId) => {
  const response = await api.patch(`/watch/${sessionId}/accept`);
  return response.data;
};

export const setReadyWatchSession = async (sessionId, isReady) => {
  const response = await api.patch(`/watch/${sessionId}/ready?is_ready=${isReady}`);
  return response.data;
};

export const triggerPlayWatchSession = async (sessionId) => {
  const response = await api.patch(`/watch/${sessionId}/play`);
  return response.data;
};

