import api from './api';

// GET /us — relationship stats, milestones, days count
export const getUsStats = async () => {
  const res = await api.get('/us');
  return res.data;
};

// PATCH /us/start-date — update relationship start date
export const updateStartDate = async (date) => {
  const res = await api.patch('/us/start-date', { date });
  return res.data;
};

// POST /us/milestones — create a new milestone / marked date
export const createMilestone = async (payload) => {
  const res = await api.post('/us/milestones', payload);
  return res.data;
};

// PATCH /us/milestones/:id — update a milestone
export const updateMilestone = async (id, payload) => {
  const res = await api.patch(`/us/milestones/${id}`, payload);
  return res.data;
};

// DELETE /us/milestones/:id — delete a milestone
export const deleteMilestone = async (id) => {
  const res = await api.delete(`/us/milestones/${id}`);
  return res.data;
};

// POST /us/next-meet — set next meet
export const setNextMeet = async (payload) => {
  const res = await api.post('/us/next-meet', payload);
  return res.data;
};

// PATCH /us/next-meet — update next meet
export const updateNextMeet = async (payload) => {
  const res = await api.patch('/us/next-meet', payload);
  return res.data;
};

// DELETE /us/next-meet — delete next meet
export const deleteNextMeet = async () => {
  const res = await api.delete('/us/next-meet');
  return res.data;
};

// GET /us/next-meet/countdown — get countdown
export const getNextMeetCountdown = async (timezone) => {
  const res = await api.get('/us/next-meet/countdown', {
    params: { viewer_timezone: timezone },
  });
  return res.data;
};
