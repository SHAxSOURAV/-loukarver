import { combineReducers, configureStore } from '@reduxjs/toolkit';
import { persistReducer, persistStore } from 'redux-persist';
import storage from "redux-persist/lib/storage";


import { baseApi } from './api/baseApi';
import { authSlice } from './features/auth/authSlice';

// Safe storage wrapper — falls back to a no-op if localStorage is blocked (e.g. Brave)
const createSafeStorage = (baseStorage) => ({
    getItem: async (key) => {
        try {
            return await baseStorage.getItem(key);
        } catch {
            return null;
        }
    },
    setItem: async (key, value) => {
        try {
            await baseStorage.setItem(key, value);
        } catch {
            // Storage blocked
        }
    },
    removeItem: async (key) => {
        try {
            await baseStorage.removeItem(key);
        } catch {
            // Storage blocked
        }
    },
});

const persistConfig = {
    key: "quiz-app",
    storage: createSafeStorage(storage),
    blacklist: ["baseApi", "logInUser"], // Prevent persisting API cache and auth
};

const rootReducer = combineReducers({
    logInUser: authSlice.reducer,
    [baseApi.reducerPath]: baseApi.reducer,
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
    reducer: persistedReducer,
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware({
            serializableCheck: {
                // Ignore redux-persist actions
                ignoredActions: ["persist/PERSIST", "persist/REHYDRATE"],
            },
        }).concat(baseApi.middleware),
});

export const persistor = persistStore(store);




// import { configureStore } from '@reduxjs/toolkit'

// import { setupListeners } from '@reduxjs/toolkit/query'
// import { baseApi } from './api/baseApi'

// export const store = configureStore({
//   reducer: {
//     [baseApi.reducerPath] :  baseApi.reducer
//   },
//   middleware : (getDefaultMiddleware)=>
//     getDefaultMiddleware().concat(baseApi.middleware)
// })
// setupListeners(store.dispatch)


