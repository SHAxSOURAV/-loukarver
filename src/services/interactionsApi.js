import api from './api';

/**
 * Send a silent ping to partner.
 * @param {string} [partnerId]
 */
export const pokePartner = async (partnerId) => {
  const payload = partnerId ? { partner_id: partnerId } : {};
  const response = await api.post('/interactions/poke', payload);
  return response.data;
};

/**
 * Get interactions count for today.
 * @param {string} [timezone]
 * @param {string} [partnerId]
 */
export const getInteractions = async (timezone = "UTC", partnerId) => {
  let url = `/interactions?timezone=${encodeURIComponent(timezone)}`;
  if (partnerId) {
    url += `&partner_id=${encodeURIComponent(partnerId)}`;
  }
  const response = await api.get(url);
  return response.data;
};
