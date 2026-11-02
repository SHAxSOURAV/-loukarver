import api from './api';

export const getStreak = async (timezone = 'UTC') => {
  const response = await api.get(`/streak?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const getWeeklyBreakdown = async (timezone = 'UTC') => {
  const response = await api.get(`/streak/weekly?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const getPartnerStreak = async (timezone = 'UTC') => {
  const response = await api.get(`/streak/partner?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};
