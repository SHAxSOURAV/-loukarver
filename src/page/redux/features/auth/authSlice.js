import { createSlice } from '@reduxjs/toolkit';

// Safe storage helpers — Brave browser may block storage access
const safeGetItem = (storage, key) => {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
};

const safeSetItem = (storage, key, value) => {
  try {
    storage.setItem(key, value);
  } catch {
    // Storage blocked — token will only live in Redux state
  }
};

const safeRemoveItem = (storage, key) => {
  try {
    storage.removeItem(key);
  } catch {
    // Storage blocked — nothing to remove
  }
};

const getInitialToken = () => {
  return safeGetItem(localStorage, 'token') || safeGetItem(sessionStorage, 'token') || null;
};

const initialState = {
  user: null,
  token: getInitialToken(),
};

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setToken: (state, action) => {
      const { token, rememberMe } = action.payload;
      state.token = token;
      if (rememberMe) {
        safeSetItem(localStorage, 'token', token);
        safeRemoveItem(sessionStorage, 'token');
      } else {
        safeSetItem(sessionStorage, 'token', token);
        safeRemoveItem(localStorage, 'token');
      }
    },
    logout: (state) => {
      state.token = null;
      safeRemoveItem(localStorage, 'token');
      safeRemoveItem(sessionStorage, 'token');
    },
  },
});

export const { setToken, logout } = authSlice.actions;

export default authSlice.reducer;