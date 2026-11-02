import api from './api';

export const proposeVibeDate = async (payload) => {
  const response = await api.post('/vibedates', payload);
  return response.data;
};

export const listVibeDates = async (partner_id, page = 1, size = 20, timezone = 'UTC') => {
  const params = new URLSearchParams({ page, size, timezone });
  if (partner_id) params.append('partner_id', partner_id);
  const response = await api.get(`/vibedates?${params.toString()}`);
  return response.data;
};

export const getVibeDateDetails = async (dateId) => {
  const response = await api.get(`/vibedates/${dateId}`);
  return response.data;
};

export const updateVibeDate = async (dateId, payload) => {
  const response = await api.patch(`/vibedates/${dateId}`, payload);
  return response.data;
};

export const deleteVibeDate = async (dateId) => {
  const response = await api.delete(`/vibedates/${dateId}`);
  return response.data;
};

export const cancelVibeDate = async (dateId) => {
  const response = await api.post(`/vibedates/${dateId}/cancel`);
  return response.data;
};

export const respondToVibeDate = async (dateId, payload) => {
  const response = await api.post(`/vibedates/${dateId}/respond`, payload);
  return response.data;
};

export const markDatesSeen = async () => {
  const response = await api.post(`/vibedates/mark-seen`);
  return response.data;
};

export const completeVibeDate = async (dateId) => {
  const response = await api.post(`/vibedates/${dateId}/complete`);
  return response.data;
};
export const hideVibeDate = async (dateId) => {
  const response = await api.post(`/vibedates/${dateId}/hide`);
  return response.data;
};

export const unhideVibeDate = async (dateId) => {
  const response = await api.post(`/vibedates/${dateId}/unhide`);
  return response.data;
};

export const listHiddenVibeDates = async (page = 1, size = 20, timezone = 'UTC') => {
  const params = new URLSearchParams({ page, size, timezone });
  const response = await api.get(`/vibedates/hidden?${params.toString()}`);
  return response.data;
};

export const deleteVibeDateForMe = async (dateId) => {
  const response = await api.post(`/vibedates/${dateId}/delete-for-me`);
  return response.data;
};
