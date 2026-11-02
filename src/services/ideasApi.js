import api from './api';

export const getBrowseIdeas = async () => {
  const response = await api.get('/ideas/browse');
  return response.data;
};

export const getCategories = async () => {
  const response = await api.get('/ideas/categories');
  return response.data;
};

export const createPersonalizedIdea = async (data) => {
  const response = await api.post('/ideas/personalized', data);
  return response.data;
};

export const updatePersonalizedIdea = async (ideaId, data) => {
  const response = await api.put(`/ideas/personalized/${ideaId}`, data);
  return response.data;
};

export const deletePersonalizedIdea = async (ideaId) => {
  const response = await api.delete(`/ideas/personalized/${ideaId}`);
  return response.data;
};

export const selectIdea = async (ideaId) => {
  const response = await api.post(`/ideas/select/${ideaId}`);
  return response.data;
};

export const acceptIdea = async (progressId) => {
  const response = await api.patch(`/ideas/active/${progressId}/accept`);
  return response.data;
};

export const markIdeaDone = async (progressId) => {
  const response = await api.patch(`/ideas/active/${progressId}/done`);
  return response.data;
};

export const getActiveIdeas = async () => {
  const response = await api.get('/ideas/active');
  return response.data;
};

export const getCompletedIdeas = async () => {
  const response = await api.get('/ideas/completed');
  return response.data;
};

export const getIncompleteIdeas = async () => {
  const response = await api.get('/ideas/incomplete');
  return response.data;
};

export const requestCancelIdea = async (progressId) => {
  const response = await api.patch(`/ideas/active/${progressId}/cancel-request`);
  return response.data;
};

export const respondCancelIdea = async (progressId, approved) => {
  const response = await api.patch(`/ideas/active/${progressId}/cancel-respond?approved=${approved}`);
  return response.data;
};
