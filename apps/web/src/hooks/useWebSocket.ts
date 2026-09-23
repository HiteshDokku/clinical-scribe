import { useRef, useCallback, useState } from 'react';
import type { TranscriptEvent } from '@/types/contracts';
import { connectWebSocket, type WebSocketManager } from '@/api/websocket';

interface UseWebSocketReturn {
  isConnected: boolean;
  connect: (encounterId: string, onTranscript: (e: TranscriptEvent) => void) => void;
  sendConsent: (value: string) => void;
  sendAudio: (data: ArrayBuffer) => void;
  sendStop: () => void;
  disconnect: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const managerRef = useRef<WebSocketManager | null>(null);

  const connect = useCallback(
    (encounterId: string, onTranscript: (e: TranscriptEvent) => void) => {
      if (managerRef.current) return;

      const manager = connectWebSocket(encounterId, {
        onTranscript,
        onError: (err) => console.error('[WS Error]', err),
        onOpen: () => setIsConnected(true),
        onClose: () => setIsConnected(false),
      });
      managerRef.current = manager;
    },
    [],
  );

  const sendConsent = useCallback((value: string) => {
    managerRef.current?.send({ t: 'consent', value: value as 'granted' });
  }, []);

  const sendAudio = useCallback((data: ArrayBuffer) => {
    managerRef.current?.sendBinary(data);
  }, []);

  const sendStop = useCallback(() => {
    managerRef.current?.send({ t: 'stop' });
  }, []);

  const disconnect = useCallback(() => {
    managerRef.current?.close();
    managerRef.current = null;
    setIsConnected(false);
  }, []);

  return { isConnected, connect, sendConsent, sendAudio, sendStop, disconnect };
}
