import type { TranscriptEvent, WsOutboundMessage } from '@/types/contracts';

type OnTranscript = (event: TranscriptEvent) => void;
type OnError = (error: string) => void;
type OnOpen = () => void;
type OnClose = () => void;

export interface WebSocketManager {
  send: (msg: WsOutboundMessage) => void;
  sendBinary: (data: ArrayBuffer) => void;
  close: () => void;
  isConnected: () => boolean;
}

/**
 * Opens a WebSocket to the gateway stream endpoint for the given encounter.
 * Receives transcript events and forwards them to the onTranscript callback.
 */
export function connectWebSocket(
  encounterId: string,
  callbacks: {
    onTranscript: OnTranscript;
    onError: OnError;
    onOpen: OnOpen;
    onClose: OnClose;
  },
): WebSocketManager {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${window.location.host}/api/v1/encounters/${encounterId}/stream`;

  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  const maxReconnects = 5;

  function connect() {
    console.log('[WS] Connecting to:', url);
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('[WS] Connected successfully.');
      reconnectAttempts = 0;
      callbacks.onOpen();
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as TranscriptEvent | { error: string };
        if ('error' in data) {
          callbacks.onError(data.error);
        } else {
          callbacks.onTranscript(data as TranscriptEvent);
        }
      } catch {
        /* Ignore unparseable messages */
      }
    };

    ws.onerror = () => {
      callbacks.onError('WebSocket connection error');
    };

    ws.onclose = () => {
      callbacks.onClose();
      if (reconnectAttempts < maxReconnects) {
        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 16000);
        setTimeout(connect, delay);
      }
    };
  }

  connect();

  return {
    send(msg: WsOutboundMessage) {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(msg));
      }
    },
    sendBinary(data: ArrayBuffer) {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    },
    close() {
      reconnectAttempts = maxReconnects; // prevent reconnect
      ws?.close();
    },
    isConnected() {
      return ws?.readyState === WebSocket.OPEN;
    },
  };
}
