import api from './api';

export const createMilestone = async (data: {
  name: string;
  why_it_matters: string;
  is_private: boolean;
  pin?: string;
  timezone: string;
}) => {
  const response = await api.post('/milestone/', data);
  return response.data;
};

export const listMilestones = async (
  page: number = 1,
  size: number = 20,
  pin: string | null = null,
  timezone: string = 'UTC'
) => {
  let url = `/milestone/?page=${page}&size=${size}&timezone=${encodeURIComponent(timezone)}`;
  if (pin) {
    url += `&pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.get(url);
  return response.data;
};

export const getMilestone = async (
  milestoneId: string,
  pin: string | null = null,
  timezone: string = 'UTC'
) => {
  let url = `/milestone/${milestoneId}?timezone=${encodeURIComponent(timezone)}`;
  if (pin) {
    url += `&pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.get(url);
  return response.data;
};

export const updateMilestone = async (
  milestoneId: string,
  data: {
    name?: string;
    why_it_matters?: string;
    is_private?: boolean;
    pin?: string;
    timezone?: string;
  },
  pin: string | null = null
) => {
  let url = `/milestone/${milestoneId}`;
  if (pin) {
    url += `?pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.patch(url, data);
  return response.data;
};

export const deleteMilestone = async (milestoneId: string, pin: string | null = null) => {
  let url = `/milestone/${milestoneId}`;
  if (pin) {
    url += `?pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.delete(url);
  return response.data;
};

export const addMilestoneStep = async (
  milestoneId: string,
  data: { text: string; timezone: string },
  pin: string | null = null
) => {
  let url = `/milestone/${milestoneId}/step`;
  if (pin) {
    url += `?pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.post(url, data);
  return response.data;
};

export const updateMilestoneStep = async (
  milestoneId: string,
  stepId: string,
  data: { text?: string; is_completed?: boolean; timezone?: string },
  pin: string | null = null
) => {
  let url = `/milestone/${milestoneId}/step/${stepId}`;
  if (pin) {
    url += `?pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.patch(url, data);
  return response.data;
};

export const deleteMilestoneStep = async (
  milestoneId: string,
  stepId: string,
  pin: string | null = null,
  timezone: string = 'UTC'
) => {
  let url = `/milestone/${milestoneId}/step/${stepId}?timezone=${encodeURIComponent(timezone)}`;
  if (pin) {
    url += `&pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.delete(url);
  return response.data;
};

export const toggleStepCompletion = async (
  milestoneId: string,
  stepId: string,
  pin: string | null = null,
  timezone: string = 'UTC'
) => {
  let url = `/milestone/${milestoneId}/step/${stepId}/toggle?timezone=${encodeURIComponent(timezone)}`;
  if (pin) {
    url += `&pin=${encodeURIComponent(pin)}`;
  }
  const response = await api.patch(url);
  return response.data;
};

export const unlockMilestone = async (milestoneId: string, data: { pin: string }) => {
  const response = await api.post(`/milestone/${milestoneId}/unlock`, data);
  return response.data;
};
