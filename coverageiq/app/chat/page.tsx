import type { Metadata } from 'next';
import ChatClient from './ChatClient';

export const metadata: Metadata = { title: 'Vantage AI' };

export default function ChatPage() {
  return <ChatClient />;
}
