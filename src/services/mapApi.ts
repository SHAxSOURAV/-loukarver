import api from './api';
import { Platform } from 'react-native';

export interface PlaceCreatePayload {
  city: string;
  country: string;
  category: 'Home' | 'Together' | 'Upcoming' | 'Bucket';
  description?: string;
  visit_date?: string; // mm.dd.yyyy
  timezone: string;
  lat?: number;
  lng?: number;
}

export interface PlaceUpdatePayload {
  city?: string;
  country?: string;
  category?: 'Home' | 'Together' | 'Upcoming' | 'Bucket';
  description?: string;
  visit_date?: string;
  timezone?: string;
}

export const createPlace = async (payload: PlaceCreatePayload) => {
  const response = await api.post('/map/place', payload);
  return response.data;
};

export const listPlaces = async (params: {
  category?: 'Home' | 'Together' | 'Upcoming' | 'Bucket';
  search?: string;
  page?: number;
  size?: number;
  timezone?: string;
}) => {
  const { category, search, page = 1, size = 20, timezone = 'UTC' } = params;
  let url = `/map/places?page=${page}&size=${size}&timezone=${encodeURIComponent(timezone)}`;
  if (category) {
    url += `&category=${encodeURIComponent(category)}`;
  }
  if (search) {
    url += `&search=${encodeURIComponent(search)}`;
  }
  const response = await api.get(url);
  return response.data;
};

export const getPlace = async (placeId: string, timezone: string = 'UTC') => {
  const response = await api.get(`/map/place/${placeId}?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const updatePlace = async (placeId: string, payload: PlaceUpdatePayload) => {
  const response = await api.patch(`/map/place/${placeId}`, payload);
  return response.data;
};

export const deletePlace = async (placeId: string) => {
  const response = await api.delete(`/map/place/${placeId}`);
  return response.data;
};

export const requestDeletePlace = async (placeId: string, timezone: string = 'Asia/Dhaka') => {
  const response = await api.post(`/map/place/${placeId}/request-delete?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const approveDeletePlace = async (placeId: string) => {
  const response = await api.post(`/map/place/${placeId}/approve-delete`);
  return response.data;
};

export const rejectDeletePlace = async (placeId: string, timezone: string = 'Asia/Dhaka') => {
  const response = await api.post(`/map/place/${placeId}/reject-delete?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const addMoment = async (
  placeId: string,
  data: {
    type: 'Photo' | 'Milestone' | 'Note' | 'Date';
    content?: string;
    caption?: string;
    timezone: string;
  },
  file?: any
) => {
  const formData = new FormData();
  formData.append('type', data.type);
  if (data.content !== undefined) {
    formData.append('content', data.content);
  }
  if (data.caption !== undefined) {
    formData.append('caption', data.caption);
  }
  formData.append('timezone', data.timezone);

  if (file) {
    if (Platform.OS === 'web') {
      const response = await fetch(file.uri);
      const blob = await response.blob();
      formData.append('file', blob, file.fileName || file.name || 'photo.jpg');
    } else {
      // React Native FormData file structure
      formData.append('file', {
        uri: file.uri,
        name: file.fileName || file.name || 'photo.jpg',
        type: file.mimeType || file.type || 'image/jpeg',
      } as any);
    }
  }

  const response = await api.post(`/map/place/${placeId}/moment`, formData);
  return response.data;
};

export const getMapStats = async (timezone: string = 'UTC') => {
  const response = await api.get(`/map/stats?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
};

export const getMapOverview = async (timezone: string = 'UTC') => {
  const response = await api.get(`/map/overview?timezone=${encodeURIComponent(timezone)}`);
  return response.data;
}
