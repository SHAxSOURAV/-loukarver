import { useState, useEffect, useRef } from 'react';
import { StorageService } from '../services/storage';

/**
 * Drop-in replacement for useState with AsyncStorage persistence.
 * Returns [value, setValue, loaded].
 */
export function usePersist<T>(
  key: string,
  initialValue: T,
): [T, React.Dispatch<React.SetStateAction<T>>, boolean] {
  const [value, setValue] = useState<T>(initialValue);
  const [loaded, setLoaded] = useState(false);
  const firstLoad = useRef(true);

  // Load from storage on mount
  useEffect(() => {
    let active = true;
    StorageService.get<T>(key).then(stored => {
      if (active && stored !== null && stored !== undefined) {
        setValue(stored);
      }
      if (active) setLoaded(true);
    });
    return () => { active = false; };
  }, [key]);

  // Persist whenever value changes (skip initial load)
  useEffect(() => {
    if (!loaded) return;
    if (firstLoad.current) { firstLoad.current = false; return; }
    StorageService.set(key, value);
  }, [key, value, loaded]);

  return [value, setValue, loaded];
}