import api from './api';

export const logPresence = async (data) => {
  const response = await api.post('/notifications/presence', data);
  return response.data;
};

export const scheduleNotification = async (data) => {
  const response = await api.post('/notifications/schedule', data);
  return response.data;
};

export const triggerNotification = async (type, message, metadata = null) => {
  const payload = { type, message };
  if (metadata) payload.metadata = metadata;
  const response = await api.post('/notifications/trigger', payload);
  return response.data;
};

export const getMyNotifications = async (page = 1, size = 20, types = null, isHidden = null) => {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  let url = `/notifications/?page=${page}&size=${size}&timezone=${encodeURIComponent(tz)}`;
  if (types && types.length > 0) {
    url += `&types=${encodeURIComponent(types.join(','))}`;
  }
  if (isHidden !== null) {
    url += `&is_hidden=${isHidden}`;
  }
  url += `&_t=${Date.now()}`;
  const response = await api.get(url);
  return response.data;
};

export const markNotificationSeen = async (id) => {
  const response = await api.patch(`/notifications/${id}/seen`);
  return response.data;
};

export const markAllNotificationsSeen = async () => {
  const response = await api.patch('/notifications/seen-all');
  return response.data;
};

export const markNotificationUnread = async (id) => {
  const response = await api.patch(`/notifications/${id}/unread`);
  return response.data;
};

export const hideNotification = async (id) => {
  const response = await api.patch(`/notifications/${id}/hide`);
  return response.data;
};

export const unhideNotification = async (id) => {
  const response = await api.patch(`/notifications/${id}/unhide`);
  return response.data;
};

export const deleteNotification = async (id) => {
  const response = await api.delete(`/notifications/${id}`);
  return response.data;
};

export const clearAllNotifications = async () => {
  const response = await api.delete(`/notifications/`);
  return response.data;
};
