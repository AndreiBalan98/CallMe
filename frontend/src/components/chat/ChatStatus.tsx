import { cn } from '@/lib/utils';
import { Phone, PhoneOff, Wifi, WifiOff } from 'lucide-react';

interface ChatStatusProps {
  isConnected: boolean;
  isCallActive: boolean;
  callerNumber?: string | null;
}

export function ChatStatus({ isConnected, isCallActive, callerNumber }: ChatStatusProps) {
  return (
    <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
      {/* Connection status */}
      <div className="flex items-center gap-2">
        {isConnected ? (
          <>
            <Wifi className="h-4 w-4 text-green-500" />
            <span className="text-sm text-green-600">Conectat</span>
          </>
        ) : (
          <>
            <WifiOff className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-600">Deconectat</span>
          </>
        )}
      </div>

      {/* Call status */}
      <div
        className={cn(
          'flex items-center gap-2 rounded-full px-3 py-1',
          isCallActive
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
        )}
      >
        {isCallActive ? (
          <>
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500"></span>
            </span>
            <Phone className="h-4 w-4" />
            <span className="text-sm font-medium">
              Apel în curs
              {callerNumber && <span className="ml-1 text-xs">({callerNumber})</span>}
            </span>
          </>
        ) : (
          <>
            <PhoneOff className="h-4 w-4" />
            <span className="text-sm">Niciun apel</span>
          </>
        )}
      </div>
    </div>
  );
}
