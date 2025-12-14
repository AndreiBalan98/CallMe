import { cn } from '@/lib/utils';

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function ScrollArea({ className, children, ...props }: ScrollAreaProps) {
  return (
    <div
      className={cn('overflow-auto scrollbar-thin scrollbar-thumb-gray-300', className)}
      {...props}
    >
      {children}
    </div>
  );
}
