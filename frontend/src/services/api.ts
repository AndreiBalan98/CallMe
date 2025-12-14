import type { ConfigResponse, Appointment } from '@/types';

const API_BASE = '/api';

/**
 * Fetch clinic configuration
 */
export async function fetchConfig(): Promise<ConfigResponse> {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) {
    throw new Error('Failed to fetch config');
  }
  return response.json();
}

/**
 * Fetch today's appointments
 */
export async function fetchAppointments(date?: string): Promise<Appointment[]> {
  const params = date ? `?filter_date=${date}` : '';
  const response = await fetch(`${API_BASE}/appointments${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch appointments');
  }
  return response.json();
}

/**
 * Create a new appointment
 */
export async function createAppointment(
  data: Omit<Appointment, 'id' | 'created_at' | 'created_by' | 'status'>
): Promise<{ success: boolean; message: string; appointment?: Appointment }> {
  const response = await fetch(`${API_BASE}/appointments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  return response.json();
}

/**
 * Delete an appointment
 */
export async function deleteAppointment(
  id: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/appointments/${id}`, {
    method: 'DELETE',
  });
  return response.json();
}
