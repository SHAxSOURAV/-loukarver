import api from './api';

export const createEnergyLog = async (data) => {
  const response = await api.post('/energy', data);
  return response.data;
};

export const getEnergyLogs = async () => {
  const response = await api.get('/energy');
  return response.data;
};

export const getPartnerEnergy = async () => {
  const response = await api.get('/energy/partner');
  return response.data;
};

export const getEnergyLog = async (logId) => {
  const response = await api.get(`/energy/${logId}`);
  return response.data;
};

export const updateEnergyLog = async (logId, data) => {
  const response = await api.put(`/energy/${logId}`, data);
  return response.data;
};

export const deleteEnergyLog = async (logId) => {
  const response = await api.delete(`/energy/${logId}`);
  return response.data;
};

export const patchShareStatus = async (logId, data) => {
  const response = await api.patch(`/energy/${logId}/share`, data);
  return response.data;
};
