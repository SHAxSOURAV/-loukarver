import api from './api';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';

/**
 * @param {string} uri
 * @param {string} [mimeType]
 * @param {string} [filename]
 * @param {((percent: number) => void) | null} [onProgress]
 */
export const uploadSecret = async (uri, mimeType = "image/jpeg", filename = "secret.jpg", onProgress = undefined) => {
  const isVideo = (mimeType && mimeType.startsWith("video")) || uri?.toLowerCase().endsWith(".mp4") || uri?.toLowerCase().endsWith(".mov");
  const actualFilename = filename || (isVideo ? "secret.mp4" : "secret.jpg");
  const actualMimeType = mimeType || (isVideo ? "video/mp4" : "image/jpeg");

  const token = await AsyncStorage.getItem('access_token');
  let baseUrl = api.defaults.baseURL || process.env.EXPO_PUBLIC_BACKEND_URL || 'https://13-61-230-140.sslip.io';
  if (baseUrl.endsWith('/')) {
    baseUrl = baseUrl.slice(0, -1);
  }
  const uploadUrl = `${baseUrl}/secret/upload`;

  // Native Mobile (Android & iOS): Industry standard FileSystem.createUploadTask with real progress
  if (Platform.OS !== 'web') {
    const uploadTask = FileSystem.createUploadTask(
      uploadUrl,
      uri,
      {
        fieldName: 'file',
        httpMethod: 'POST',
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        mimeType: actualMimeType,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        parameters: {
          prevent_screenshot: 'true',
          delete_after: '24 Hours',
        },
      },
      (data) => {
        if (data && data.totalBytesExpectedToSend > 0) {
          const percent = Math.min(
            100,
            Math.max(0, Math.round((data.totalBytesSent / data.totalBytesExpectedToSend) * 100))
          );
          if (typeof onProgress === 'function') {
            onProgress(percent);
          }
        }
      }
    );

    const uploadResult = await uploadTask.uploadAsync();

    if (uploadResult && uploadResult.status >= 200 && uploadResult.status < 300) {
      try {
        return JSON.parse(uploadResult.body);
      } catch (e) {
        return { success: true };
      }
    } else {
      let errorDetail = `Upload failed with status ${uploadResult?.status || 'unknown'}`;
      try {
        if (uploadResult?.body) {
          const parsed = JSON.parse(uploadResult.body);
          if (parsed.detail) errorDetail = parsed.detail;
        }
      } catch (e) {}
      throw new Error(errorDetail);
    }
  }

  // Web fallback: XMLHttpRequest with upload progress
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    fetch(uri)
      .then((res) => res.blob())
      .then((blob) => {
        formData.append("file", blob, actualFilename);
        formData.append("prevent_screenshot", "true");
        formData.append("delete_after", "24 Hours");

        const xhr = new XMLHttpRequest();
        xhr.open("POST", uploadUrl);
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);

        if (xhr.upload && typeof onProgress === 'function') {
          xhr.upload.onprogress = (event) => {
            if (event.lengthComputable && event.total > 0) {
              const percent = Math.min(100, Math.max(0, Math.round((event.loaded / event.total) * 100)));
              onProgress(percent);
            }
          };
        }

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch (e) {
              resolve({ success: true });
            }
          } else {
            let errorDetail = `Upload failed with status ${xhr.status}`;
            try {
              const parsed = JSON.parse(xhr.responseText);
              if (parsed.detail) errorDetail = parsed.detail;
            } catch (e) {}
            reject(new Error(errorDetail));
          }
        };

        xhr.onerror = () => {
          reject(new Error("Network error during upload"));
        };

        xhr.send(formData);
      })
      .catch(reject);
  });
};

export const getReceivedSecrets = async () => {
  const response = await api.get('/secret/received');
  return response.data;
};

export const getSentSecrets = async () => {
  const response = await api.get('/secret/sent');
  return response.data;
};

export const patchScreenshotProtection = async (secretId) => {
  const response = await api.patch(`/secret/${secretId}/screenshot`);
  return response.data;
};

// Returns streaming metadata URL for the given secret
export const getSecretViewUrl = (secretId) => {
  return `${api.defaults.baseURL}/secret/view-url/${secretId}`;
};

/**
 * Retrieves the direct viewing URL & metadata for a secret.
 * Resolves full remote URL for streaming video / image.
 * Resilient against both /view-url and /view routes.
 */
export const getSecretViewInfo = async (secretIdOrObj) => {
  const secretId = typeof secretIdOrObj === 'object' && secretIdOrObj !== null
    ? (secretIdOrObj.id || secretIdOrObj._id)
    : secretIdOrObj;

  if (!secretId) {
    throw new Error('Invalid secret ID provided to view');
  }

  let response;
  try {
    response = await api.get(`/secret/view-url/${secretId}`);
  } catch (err) {
    response = await api.get(`/secret/view/${secretId}`);
  }
  const data = response.data?.data || response.data;
  if (data?.url && !data.url.startsWith('http')) {
    let baseUrl = api.defaults.baseURL || process.env.EXPO_PUBLIC_BACKEND_URL || 'https://13-61-230-140.sslip.io';
    if (baseUrl.endsWith('/')) {
      baseUrl = baseUrl.slice(0, -1);
    }
    const path = data.url.startsWith('/') ? data.url : `/${data.url}`;
    data.url = `${baseUrl}${path}`;
  }
  return data;
};

export const requestRewatchSecret = async (secretId) => {
  const response = await api.post(`/secret/${secretId}/rewatch/request`);
  return response.data;
};

export const approveRewatchSecret = async (secretId) => {
  const response = await api.post(`/secret/${secretId}/rewatch/approve`);
  return response.data;
};

export const declineRewatchSecret = async (sessionId) => {
  const response = await api.post(`/secret/${sessionId}/rewatch/decline`);
  return response.data;
};

export const revokeSecret = async (sessionId) => {
  const response = await api.delete(`/secret/${sessionId}/revoke`);
  return response.data;
};
