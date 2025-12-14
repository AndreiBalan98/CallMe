import { create } from 'zustand';
import type { Clinic, Doctor, Service, Appointment, ConfigResponse } from '@/types';

interface ScheduleState {
  // Config data
  clinic: Clinic | null;
  doctors: Doctor[];
  services: Service[];
  appointments: Appointment[];
  today: string;
  
  // Loading state
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setConfig: (config: ConfigResponse) => void;
  addAppointment: (appointment: Appointment) => void;
  updateAppointment: (appointment: Appointment) => void;
  removeAppointment: (appointmentId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Selectors
  getServiceById: (id: string) => Service | undefined;
  getDoctorById: (id: string) => Doctor | undefined;
  getAppointmentsForDoctor: (doctorId: string) => Appointment[];
}

export const useScheduleStore = create<ScheduleState>((set, get) => ({
  clinic: null,
  doctors: [],
  services: [],
  appointments: [],
  today: new Date().toISOString().split('T')[0],
  isLoading: true,
  error: null,
  
  setConfig: (config) => {
    set({
      clinic: config.clinic,
      doctors: config.doctors,
      services: config.services,
      appointments: config.appointments,
      today: config.today,
      isLoading: false,
      error: null,
    });
  },
  
  addAppointment: (appointment) => {
    set((state) => ({
      appointments: [...state.appointments, appointment],
    }));
  },
  
  updateAppointment: (appointment) => {
    set((state) => ({
      appointments: state.appointments.map((apt) =>
        apt.id === appointment.id ? appointment : apt
      ),
    }));
  },
  
  removeAppointment: (appointmentId) => {
    set((state) => ({
      appointments: state.appointments.filter((apt) => apt.id !== appointmentId),
    }));
  },
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error, isLoading: false }),
  
  getServiceById: (id) => {
    return get().services.find((s) => s.id === id);
  },
  
  getDoctorById: (id) => {
    return get().doctors.find((d) => d.id === id);
  },
  
  getAppointmentsForDoctor: (doctorId) => {
    return get().appointments.filter((apt) => apt.doctor_id === doctorId);
  },
}));
