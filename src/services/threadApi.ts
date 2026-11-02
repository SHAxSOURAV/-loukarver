import api from './api';
import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';

const readUriAsBase64 = async (uri: string): Promise<string> => {
  if (Platform.OS === 'web') {
    const response = await fetch(uri);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result.split(',')[1]);
        } else {
          reject(new Error('Failed to read as base64'));
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } else {
    return await FileSystem.readAsStringAsync(uri, { encoding: 'base64' });
  }
};

export const getThreadCategories = async () => {
  const response = await api.get('/thread/categories');
  return response.data;
};

export const getThreadMessages = async (page = 1, size = 20, timezone = 'UTC') => {
  const response = await api.get(`/thread/messages?page=${page}&size=${size}&timezone=${encodeURIComponent(timezone)}`);
  return response.data; // should return the array directly based on router logic
};

export const deleteThreadMessage = async (messageId: string) => {
  const response = await api.delete(`/thread/${messageId}`);
  return response.data;
};

export const postLetter = async (payload: { text: string; timezone?: string }) => {
  const response = await api.post('/thread/letter', { ...payload, category: 'Letter' });
  return response.data;
};

export const patchLetter = async (messageId: string, payload: { text: string; timezone?: string }) => {
  const response = await api.patch(`/thread/letter/${messageId}`, payload);
  return response.data;
};

export const postVoice = async (file: any, timezone: string = 'UTC') => {
  const base64 = await readUriAsBase64(file.uri);
  const payload = {
    file_base64: base64,
    filename: file.name || 'voice.m4a',
    content_type: file.type || 'audio/m4a',
    category: 'Voice',
    timezone
  };
  const response = await api.post('/thread/voice_base64', payload);
  return response.data;
};

export const postPhoto = async (file: any, caption: string, timezone: string = 'UTC') => {
  const base64 = await readUriAsBase64(file.uri);
  const payload = {
    file_base64: base64,
    filename: file.name || 'photo.jpg',
    content_type: file.type || 'image/jpeg',
    caption,
    category: 'Photo',
    timezone
  };
  const response = await api.post('/thread/photo_base64', payload);
  return response.data;
};

export const askPrompt = async (payload: { prompt_type: string; question_text: string; type: string; timezone?: string }) => {
  const response = await api.post('/thread/prompt/ask', { ...payload, category: 'Prompt' });
  return response.data;
};

export const replyToPrompt = async (messageId: string, payload: { answer: string; timezone?: string }) => {
  const response = await api.post(`/thread/prompt/${messageId}/reply`, payload);
  return response.data;
};

export const postAppreciation = async (payload: { text: string; timezone?: string }) => {
  const response = await api.post('/thread/appreciation', { ...payload, category: 'Appreciation' });
  return response.data;
};

export const postCheckin = async (payload: { date: string; answer_1: string; answer_2: string; answer_3: string; timezone?: string }) => {
  const response = await api.post('/thread/checkin', { ...payload, category: 'Checkin' });
  return response.data;
};

export const getPromptQuestions = async (type: string) => {
  const response = await api.get(`/thread/prompt/questions?type=${type}`);
  return response.data;
};

export const deleteMessage = async (messageId: string, mode: 'me' | 'everyone' = 'everyone') => {
  const response = await api.delete(`/thread/${messageId}?mode=${mode}`);
  return response.data;
};
