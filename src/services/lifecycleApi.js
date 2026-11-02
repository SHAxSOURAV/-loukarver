import api from './api';

export const getLifecycleOverview = async () => {
  const response = await api.get('/lifecycle');
  return response.data;
};

export const addPeriodStart = async (data) => {
  const response = await api.post('/lifecycle/period', data);
  return response.data;
};

export const updatePeriodStart = async (periodId, data) => {
  const response = await api.patch(`/lifecycle/period/${periodId}`, data);
  return response.data;
};

export const deletePeriodRecord = async (periodId) => {
  const response = await api.delete(`/lifecycle/period/${periodId}`);
  return response.data;
};

export const addPhaseNote = async (data) => {
  const response = await api.post('/lifecycle/note', data);
  return response.data;
};

export const updatePhaseNote = async (noteId, data) => {
  const response = await api.patch(`/lifecycle/note/${noteId}`, data);
  return response.data;
};

export const deletePhaseNote = async (noteId) => {
  const response = await api.delete(`/lifecycle/note/${noteId}`);
  return response.data;
};

export const toggleCycleSharing = async (is_shared) => {
  const response = await api.patch('/lifecycle/settings/share', { is_shared });
  return response.data;
};
