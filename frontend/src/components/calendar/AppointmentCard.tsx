import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { useScheduleStore } from '@/stores/scheduleStore';
import type { Appointment } from '@/types';
import { User, Phone, Clock } from 'lucide-react';

interface AppointmentCardProps {
  appointment: Appointment;
  isNew?: boolean;
}

export function AppointmentCard({ appointment, isNew }: AppointmentCardProps) {
  const { getServiceById } = useScheduleStore();
  const service = getServiceById(appointment.service_id);

  return (
    <div
      className={cn(
        'rounded-lg border p-2 transition-all',
        isNew
          ? 'animate-pulse border-green-400 bg-green-50'
          : 'border-primary-200 bg-primary-50'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <User className="h-3 w-3 text-gray-500" />
            <span className="text-sm font-medium text-gray-900">
              {appointment.patient_name}
            </span>
          </div>
          
          <div className="flex items-center gap-1.5">
            <Phone className="h-3 w-3 text-gray-400" />
            <span className="text-xs text-gray-500">
              {appointment.patient_phone}
            </span>
          </div>
        </div>

        <Badge
          variant={appointment.created_by.includes('ai') ? 'success' : 'outline'}
          className="text-[10px]"
        >
          {appointment.created_by.includes('ai') ? 'AI' : 'Manual'}
        </Badge>
      </div>

      {service && (
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-gray-600">{service.name}</span>
          <span className="text-xs font-medium text-primary-600">
            {service.price} RON
          </span>
        </div>
      )}
    </div>
  );
}
