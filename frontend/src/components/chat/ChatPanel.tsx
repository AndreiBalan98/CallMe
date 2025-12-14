import { useEffect, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatMessage } from './ChatMessage';
import { ChatStatus } from './ChatStatus';
import { useConversationStore } from '@/stores/conversationStore';
import { MessageSquare } from 'lucide-react';

export function ChatPanel() {
  const { isConnected, call, messages } = useConversationStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <Card className="flex h-full flex-col">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary-500" />
          Conversație Live
        </CardTitle>
      </CardHeader>

      <ChatStatus
        isConnected={isConnected}
        isCallActive={call.isActive}
        callerNumber={call.callerNumber}
      />

      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea ref={scrollRef} className="h-full p-4">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-gray-400">
              <MessageSquare className="mb-4 h-12 w-12 opacity-50" />
              <p className="text-center">
                Conversația va apărea aici când
                <br />
                un pacient sună la clinică.
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
