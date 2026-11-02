import api from './api';

export const getQuestionsEndpoint = async () => {
  const response = await api.get('/check-in/questions');
  return response.data;
};

export const getCheckin = async (date) => {
  const response = await api.get(`/check-in?date=${encodeURIComponent(date)}`);
  return response.data;
};

export const createCheckin = async (data) => {
  const response = await api.post('/check-in', data);
  return response.data;
};

export const updateCheckin = async (data) => {
  const response = await api.patch('/check-in', data);
  return response.data;
};
