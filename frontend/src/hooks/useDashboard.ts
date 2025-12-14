import { useEffect, useRef, useCallback } from 'react';
import { useConversationStore } from '@/stores/conversationStore';
import { useScheduleStore } from '@/stores/scheduleStore';
import type { DashboardEvent, TranscriptData, CallStartedData, CallEndedData, AppointmentEventData } from '@/types';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/dashboard`;
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useDashboardWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  const { setConnected, startCall, endCall, addUserMessage, addAgentMessage, updateLastAgentMessage } = useConversationStore();
  const { addAppointment, updateAppointment, removeAppointment } = useScheduleStore();
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    console.log('Connecting to dashboard WebSocket...');
    
    try {
      wsRef.current = new WebSocket(WS_URL);
      
      wsRef.current.onopen = () => {
        console.log('Dashboard WebSocket connected');
        setConnected(true);
        reconnectAttempts.current = 0;
      };
      
      wsRef.current.onclose = (event) => {
        console.log('Dashboard WebSocket closed:', event.code, event.reason);
        setConnected(false);
        
        // Attempt reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          console.log(`Reconnecting in ${RECONNECT_DELAY}ms (attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_DELAY);
        }
      };
      
      wsRef.current.onerror = (error) => {
        console.error('Dashboard WebSocket error:', error);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const message: DashboardEvent = JSON.parse(event.data);
          handleMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }, [setConnected]);
  
  const handleMessage = useCallback((message: DashboardEvent) => {
    switch (message.type) {
      case 'connection_status':
        console.log('Connection status:', message.data);
        break;
        
      case 'call_started': {
        const data = message.data as CallStartedData;
        startCall(data.call_id, data.caller_number);
        break;
      }
      
      case 'call_ended': {
        endCall();
        break;
      }
      
      case 'transcript_user': {
        const data = message.data as TranscriptData;
        addUserMessage(data.text, data.is_final);
        break;
      }
      
      case 'transcript_agent': {
        const data = message.data as TranscriptData;
        if (data.is_final) {
          addAgentMessage(data.text);
        } else {
          updateLastAgentMessage(data.text);
        }
        break;
      }
      
      case 'appointment_created': {
        const data = message.data as AppointmentEventData;
        addAppointment(data.appointment);
        break;
      }
      
      case 'appointment_updated': {
        const data = message.data as AppointmentEventData;
        updateAppointment(data.appointment);
        break;
      }
      
      case 'appointment_deleted': {
        const appointmentId = message.data.appointment_id as string;
        removeAppointment(appointmentId);
        break;
      }
      
      case 'error':
        console.error('Server error:', message.data);
        break;
        
      case 'pong':
        // Heartbeat response
        break;
        
      default:
        console.log('Unknown message type:', message.type);
    }
  }, [startCall, endCall, addUserMessage, addAgentMessage, updateLastAgentMessage, addAppointment, updateAppointment, removeAppointment]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnected(false);
  }, [setConnected]);
  
  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'ping' }));
    }
  }, []);
  
  // Connect on mount
  useEffect(() => {
    connect();
    
    // Heartbeat
    const pingInterval = setInterval(sendPing, 30000);
    
    return () => {
      clearInterval(pingInterval);
      disconnect();
    };
  }, [connect, disconnect, sendPing]);
  
  return {
    connect,
    disconnect,
    sendPing,
  };
}
