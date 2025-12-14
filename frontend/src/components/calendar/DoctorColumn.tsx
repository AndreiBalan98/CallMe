import { useMemo } from 'react';
import { TimeSlot } from './TimeSlot';
import { Badge } from '@/components/ui/badge';
import { useScheduleStore } from '@/stores/scheduleStore';
import { generateTimeSlots } from '@/lib/utils';
import type { Doctor, Appointment } from '@/types';
import { Stethoscope } from 'lucide-react';

interface DoctorColumnProps {
  doctor: Doctor;
  newAppointmentIds?: Set<string>;
}

export function DoctorColumn({ doctor, newAppointmentIds = new Set() }: DoctorColumnProps) {
  const { clinic, getAppointmentsForDoctor } = useScheduleStore();
  const appointments = getAppointmentsForDoctor(doctor.id);

  // Generate all time slots for the day
  const timeSlots = useMemo(() => {
    if (!clinic?.working_hours) return [];
    
    const slots = generateTimeSlots(
      clinic.working_hours.start,
      clinic.working_hours.end,
      clinic.working_hours.slot_duration_minutes
    );

    // Map appointments to slots
    const appointmentMap = new Map<string, Appointment>();
    appointments.forEach((apt) => {
      appointmentMap.set(apt.time, apt);
    });

    return slots.map((time) => ({
      time,
      appointment: appointmentMap.get(time) || null,
    }));
  }, [clinic, appointments]);

  const bookedCount = appointments.length;
  const totalSlots = timeSlots.length;
  const availableCount = totalSlots - bookedCount;

  return (
    <div className="flex flex-col rounded-lg border border-gray-200 bg-white">
      {/* Doctor header */}
      <div className="border-b border-gray-200 bg-gray-50 p-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-dental-light text-dental-dark">
            <Stethoscope className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">{doctor.name}</h3>
            <p className="text-xs text-gray-500">{doctor.specialization}</p>
          </div>
        </div>
        
        <div className="mt-2 flex gap-2">
          <Badge variant="success" className="text-[10px]">
            {availableCount} libere
          </Badge>
          <Badge variant="default" className="text-[10px]">
            {bookedCount} programări
          </Badge>
        </div>
      </div>

      {/* Time slots */}
      <div className="flex-1 overflow-auto">
        {timeSlots.map(({ time, appointment }) => (
          <TimeSlot
            key={time}
            time={time}
            appointment={appointment}
            isNew={appointment ? newAppointmentIds.has(appointment.id) : false}
          />
        ))}
      </div>
    </div>
  );
}
