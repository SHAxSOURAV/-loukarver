import api from './api';

export const getMoodList = async () => {
  const response = await api.get('/mood/list');
  return response.data;
};

export const createMoodOption = async (data) => {
  const response = await api.post('/mood/list', data);
  return response.data;
};

export const updateMoodOption = async (moodId, data) => {
  const response = await api.put(`/mood/list/${moodId}`, data);
  return response.data;
};

export const deleteMoodOption = async (moodId) => {
  const response = await api.delete(`/mood/list/${moodId}`);
  return response.data;
};

export const getCurrentMood = async () => {
  const response = await api.get('/mood/current');
  return response.data;
};

export const getMoodHistory = async () => {
  const response = await api.get('/mood/history');
  return response.data;
};

export const logMood = async (data) => {
  const response = await api.post('/mood', data);
  return response.data;
};

export const updateLoggedMood = async (logId, data) => {
  const response = await api.put(`/mood/${logId}`, data);
  return response.data;
};

export const deleteLoggedMood = async (logId) => {
  const response = await api.delete(`/mood/${logId}`);
  return response.data;
};
