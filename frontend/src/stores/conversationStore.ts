import { create } from 'zustand';
import type { ChatMessage } from '@/types';
import { generateId } from '@/lib/utils';

interface CallState {
  isActive: boolean;
  callId: string | null;
  callerNumber: string | null;
  startTime: Date | null;
}

interface ConversationState {
  // Connection status
  isConnected: boolean;
  
  // Current call
  call: CallState;
  
  // Chat messages
  messages: ChatMessage[];
  
  // Actions
  setConnected: (connected: boolean) => void;
  startCall: (callId: string, callerNumber: string) => void;
  endCall: () => void;
  addUserMessage: (text: string, isFinal: boolean) => void;
  addAgentMessage: (text: string) => void;
  addSystemMessage: (text: string) => void;
  updateLastAgentMessage: (text: string) => void;
  clearMessages: () => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  isConnected: false,
  
  call: {
    isActive: false,
    callId: null,
    callerNumber: null,
    startTime: null,
  },
  
  messages: [],
  
  setConnected: (connected) => set({ isConnected: connected }),
  
  startCall: (callId, callerNumber) => {
    set({
      call: {
        isActive: true,
        callId,
        callerNumber,
        startTime: new Date(),
      },
      messages: [], // Clear previous messages
    });
    
    // Add system message
    get().addSystemMessage('Apel nou conectat');
  },
  
  endCall: () => {
    const { call } = get();
    if (call.startTime) {
      const duration = Math.round(
        (new Date().getTime() - call.startTime.getTime()) / 1000
      );
      get().addSystemMessage(`Apel încheiat (${duration} secunde)`);
    }
    
    set({
      call: {
        isActive: false,
        callId: null,
        callerNumber: null,
        startTime: null,
      },
    });
  },
  
  addUserMessage: (text, isFinal) => {
    const { messages } = get();
    
    // If we have a pending user message, update it
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.type === 'user' && !lastMessage.isFinal) {
      set({
        messages: messages.map((m, i) =>
          i === messages.length - 1 ? { ...m, text, isFinal } : m
        ),
      });
    } else {
      // Add new message
      set({
        messages: [
          ...messages,
          {
            id: generateId(),
            type: 'user',
            text,
            timestamp: new Date(),
            isFinal,
          },
        ],
      });
    }
  },
  
  addAgentMessage: (text) => {
    set({
      messages: [
        ...get().messages,
        {
          id: generateId(),
          type: 'agent',
          text,
          timestamp: new Date(),
          isFinal: true,
        },
      ],
    });
  },
  
  updateLastAgentMessage: (text) => {
    const { messages } = get();
    const lastAgentIndex = messages.findLastIndex((m) => m.type === 'agent');
    
    if (lastAgentIndex >= 0 && !messages[lastAgentIndex].isFinal) {
      set({
        messages: messages.map((m, i) =>
          i === lastAgentIndex ? { ...m, text: m.text + text } : m
        ),
      });
    } else {
      // Create new agent message
      set({
        messages: [
          ...messages,
          {
            id: generateId(),
            type: 'agent',
            text,
            timestamp: new Date(),
            isFinal: false,
          },
        ],
      });
    }
  },
  
  addSystemMessage: (text) => {
    set({
      messages: [
        ...get().messages,
        {
          id: generateId(),
          type: 'system',
          text,
          timestamp: new Date(),
          isFinal: true,
        },
      ],
    });
  },
  
  clearMessages: () => set({ messages: [] }),
}));
