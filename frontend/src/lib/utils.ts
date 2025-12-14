import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format time string (HH:MM) to display format
 */
export function formatTime(time: string): string {
  return time;
}

/**
 * Format date to Romanian locale
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('ro-RO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

/**
 * Format date short
 */
export function formatDateShort(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('ro-RO', {
    day: 'numeric',
    month: 'short',
  });
}

/**
 * Format timestamp to time
 */
export function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('ro-RO', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Generate time slots for a day
 */
export function generateTimeSlots(
  start: string,
  end: string,
  durationMinutes: number
): string[] {
  const slots: string[] = [];
  const [startHour, startMin] = start.split(':').map(Number);
  const [endHour, endMin] = end.split(':').map(Number);

  let currentHour = startHour;
  let currentMin = startMin;

  while (
    currentHour < endHour ||
    (currentHour === endHour && currentMin < endMin)
  ) {
    slots.push(
      `${currentHour.toString().padStart(2, '0')}:${currentMin.toString().padStart(2, '0')}`
    );
    currentMin += durationMinutes;
    if (currentMin >= 60) {
      currentHour += 1;
      currentMin = currentMin - 60;
    }
  }

  return slots;
}

/**
 * Generate unique ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2, 10);
}
