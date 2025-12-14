import { cn } from '@/lib/utils';
import { AppointmentCard } from './AppointmentCard';
import type { Appointment } from '@/types';

interface TimeSlotProps {
  time: string;
  appointment: Appointment | null;
  isNew?: boolean;
}

export function TimeSlot({ time, appointment, isNew }: TimeSlotProps) {
  const hasAppointment = appointment !== null;

  return (
    <div
      className={cn(
        'min-h-[4rem] border-b border-gray-100 p-1 transition-colors',
        !hasAppointment && 'hover:bg-gray-50'
      )}
    >
      <div className="flex h-full gap-2">
        {/* Time label */}
        <div className="w-12 shrink-0 pt-1">
          <span className="text-xs font-medium text-gray-400">{time}</span>
        </div>

        {/* Slot content */}
        <div className="flex-1">
          {hasAppointment ? (
            <AppointmentCard appointment={appointment} isNew={isNew} />
          ) : (
            <div className="flex h-full items-center justify-center rounded-lg border border-dashed border-gray-200">
              <span className="text-xs text-gray-300">Liber</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
