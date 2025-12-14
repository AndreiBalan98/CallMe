import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { DoctorColumn } from './DoctorColumn';
import { useScheduleStore } from '@/stores/scheduleStore';
import { formatDate } from '@/lib/utils';
import { Calendar, RefreshCw } from 'lucide-react';

export function CalendarPanel() {
  const { doctors, today, appointments, isLoading } = useScheduleStore();
  const [newAppointmentIds, setNewAppointmentIds] = useState<Set<string>>(new Set());

  // Track new appointments for animation
  useEffect(() => {
    if (appointments.length > 0) {
      const latestAppointment = appointments[appointments.length - 1];
      
      // Check if this is a new appointment (created in the last 5 seconds)
      const createdAt = new Date(latestAppointment.created_at);
      const now = new Date();
      const diffSeconds = (now.getTime() - createdAt.getTime()) / 1000;
      
      if (diffSeconds < 5) {
        setNewAppointmentIds((prev) => new Set([...prev, latestAppointment.id]));
        
        // Remove highlight after 5 seconds
        setTimeout(() => {
          setNewAppointmentIds((prev) => {
            const next = new Set(prev);
            next.delete(latestAppointment.id);
            return next;
          });
        }, 5000);
      }
    }
  }, [appointments]);

  if (isLoading) {
    return (
      <Card className="flex h-full items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </Card>
    );
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary-500" />
            Program Ziua de Azi
          </CardTitle>
          <span className="text-sm text-gray-500">{formatDate(today)}</span>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-4 pt-2">
        <div className="grid h-full grid-cols-3 gap-4">
          {doctors.map((doctor) => (
            <DoctorColumn
              key={doctor.id}
              doctor={doctor}
              newAppointmentIds={newAppointmentIds}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
