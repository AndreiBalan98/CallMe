// Clinic data types
export interface Clinic {
  name: string;
  phone: string;
  address: string;
  greeting_templates: string[];
  working_hours: WorkingHours;
}

export interface WorkingHours {
  start: string;
  end: string;
  slot_duration_minutes: number;
}

export interface Doctor {
  id: string;
  name: string;
  specialization: string;
  available_services: string[];
}

export interface Service {
  id: string;
  name: string;
  price: number;
  duration_minutes: number;
  description: string;
}

export interface Appointment {
  id: string;
  doctor_id: string;
  date: string;
  time: string;
  patient_name: string;
  patient_phone: string;
  service_id: string;
  created_at: string;
  created_by: string;
  status: string;
}

// WebSocket event types
export type EventType =
  | 'call_started'
  | 'call_ended'
  | 'transcript_user'
  | 'transcript_agent'
  | 'appointment_created'
  | 'appointment_updated'
  | 'appointment_deleted'
  | 'connection_status'
  | 'error'
  | 'pong';

export interface DashboardEvent {
  type: EventType;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface CallStartedData {
  call_id: string;
  caller_number: string;
}

export interface CallEndedData {
  call_id: string;
  duration_seconds: number;
}

export interface TranscriptData {
  call_id: string;
  text: string;
  is_final: boolean;
}

export interface AppointmentEventData {
  appointment: Appointment;
}

export interface ConnectionStatusData {
  status: 'connected' | 'disconnected' | 'reconnecting';
  message: string;
}

// Chat message for display
export interface ChatMessage {
  id: string;
  type: 'user' | 'agent' | 'system';
  text: string;
  timestamp: Date;
  isFinal: boolean;
}

// Config response from API
export interface ConfigResponse {
  clinic: Clinic;
  doctors: Doctor[];
  services: Service[];
  appointments: Appointment[];
  today: string;
}

// Time slot for calendar
export interface TimeSlot {
  time: string;
  appointment: Appointment | null;
  isAvailable: boolean;
}
