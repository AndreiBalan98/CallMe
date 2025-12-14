import { ChatPanel } from '@/components/chat/ChatPanel';
import { CalendarPanel } from '@/components/calendar/CalendarPanel';
import { useScheduleStore } from '@/stores/scheduleStore';
import { useDashboardWebSocket } from '@/hooks/useDashboard';
import { useClinicData } from '@/hooks/useClinicData';

export function Dashboard() {
  const { clinic, error } = useScheduleStore();
  
  // Load clinic data on mount
  useClinicData();
  
  // Connect to WebSocket
  useDashboardWebSocket();

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100">
        <div className="rounded-lg bg-white p-8 shadow-lg">
          <h2 className="mb-2 text-xl font-semibold text-red-600">Eroare</h2>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg bg-primary-500 px-4 py-2 text-white hover:bg-primary-600"
          >
            Reîncearcă
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-100">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-6 py-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-dental text-white">
              <span className="text-xl">🦷</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                {clinic?.name || 'Clinica Dentară'}
              </h1>
              <p className="text-sm text-gray-500">Dashboard Asistent Vocal</p>
            </div>
          </div>
          
          {clinic && (
            <div className="text-right text-sm text-gray-500">
              <p>{clinic.phone}</p>
              <p>{clinic.address}</p>
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex flex-1 gap-4 overflow-hidden p-4">
        {/* Left panel - Chat (50%) */}
        <div className="w-1/2">
          <ChatPanel />
        </div>

        {/* Right panel - Calendar (50%) */}
        <div className="w-1/2">
          <CalendarPanel />
        </div>
      </main>
    </div>
  );
}
