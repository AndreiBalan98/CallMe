import { cn, formatTimestamp } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/types';
import { User, Bot, Info } from 'lucide-react';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center py-2">
        <div className="flex items-center gap-2 rounded-full bg-gray-100 px-4 py-1.5 text-xs text-gray-600">
          <Info className="h-3 w-3" />
          <span>{message.text}</span>
          <span className="text-gray-400">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex gap-3 py-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary-100 text-primary-600' : 'bg-dental-light text-dental-dark'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Message bubble */}
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-2',
          isUser
            ? 'bg-primary-500 text-white'
            : 'bg-gray-100 text-gray-900',
          !message.isFinal && 'opacity-70'
        )}
      >
        <p className="text-sm leading-relaxed">{message.text}</p>
        <span
          className={cn(
            'mt-1 block text-right text-xs',
            isUser ? 'text-primary-200' : 'text-gray-400'
          )}
        >
          {formatTimestamp(message.timestamp)}
          {!message.isFinal && ' ...'}
        </span>
      </div>
    </div>
  );
}
