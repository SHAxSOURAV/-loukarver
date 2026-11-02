import api from './api';

export const completeRitual = async (data) => {
  const formData = new FormData();
  for (const key in data) {
    if (data[key] !== undefined && data[key] !== null) {
      formData.append(key, data[key]);
    }
  }
  
  const response = await api.post('/rituals/complete', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getRitualHistory = async (page = 1, limit = 30, timezone = 'UTC') => {
  const response = await api.get(`/rituals/history?page=${page}&limit=${limit}&timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const getPartnerRituals = async (page = 1, limit = 30, timezone = 'UTC') => {
  const response = await api.get(`/rituals/partner-history?page=${page}&limit=${limit}&timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const updateRitualVisibility = async (ritualId, action) => {
  const response = await api.patch(`/rituals/${ritualId}/visibility?action=${action}`);
  return response.data;
};

