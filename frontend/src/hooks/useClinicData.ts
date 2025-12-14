import { useEffect } from 'react';
import { useScheduleStore } from '@/stores/scheduleStore';
import { fetchConfig } from '@/services/api';

export function useClinicData() {
  const { setConfig, setError, setLoading, isLoading, error } = useScheduleStore();
  
  useEffect(() => {
    const loadConfig = async () => {
      setLoading(true);
      try {
        const config = await fetchConfig();
        setConfig(config);
      } catch (e) {
        console.error('Failed to load clinic config:', e);
        setError('Nu s-au putut încărca datele clinicii');
      }
    };
    
    loadConfig();
  }, [setConfig, setError, setLoading]);
  
  return { isLoading, error };
}
