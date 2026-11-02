import api from './api';

export const setVibePulse = async (partner_id, status) => {
  const res = await api.post('/ladder', { partner_id, status });
  return res.data;
};

export const listVibePulses = async () => {
  const res = await api.get('/ladder');
  return res.data;
};

export const getVibePulseStatus = async (partner_id) => {
  const res = await api.get(`/ladder/${partner_id}`);
  return res.data;
};

export const deleteVibePulse = async (partner_id) => {
  const res = await api.delete(`/ladder/${partner_id}`);
  return res.data;
};

export const checkAlignedConnection = async (partner_id) => {
  const res = await api.get(`/ladder/check-aligned/${partner_id}`);
  return res.data;
};

export const breakAlignment = async (password) => {
  const res = await api.post('/users/break-alignment', { password });
  return res.data;
};

export const getPulseAnalytics = async (partner_id) => {
  const params = partner_id ? { partner_id } : {};
  const res = await api.get('/ladder/insights/analytics', { params });
  return res.data;
};

// Flags
export const createFlag = async (partner_id, category, type, text, timezone = "UTC") => {
  const res = await api.post('/ladder/flags', {
    partner_id, category, type, text, timezone
  });
  return res.data;
};

export const getMyFlags = async (partner_id) => {
  const params = partner_id ? { partner_id } : {};
  const res = await api.get('/ladder/flags', { params });
  return res.data;
};

export const getPartnerFlags = async (partner_id) => {
  const res = await api.get(`/ladder/flags/partner/${partner_id}`);
  return res.data;
};

export const updateFlag = async (flag_id, updates) => {
  const res = await api.patch(`/ladder/flags/${flag_id}`, updates);
  return res.data;
};

export const deleteFlag = async (flag_id) => {
  const res = await api.delete(`/ladder/flags/${flag_id}`);
  return res.data;
};
