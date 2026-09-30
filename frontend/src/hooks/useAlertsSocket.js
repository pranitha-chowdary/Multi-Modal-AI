/**
 * Streams real-time JSON alerts/action-plans from the ADIS backend over
 * WebSocket, no polling. Auto-reconnects with backoff if the connection drops.
 */
import { useEffect, useRef, useState } from "react";

export function useAlertsSocket(path = "/ws/alerts") {
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1000);

  useEffect(() => {
    let socket;
    let retryTimeout;
    let cancelled = false;

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(`${protocol}//${window.location.host}${path}`);

      socket.onopen = () => {
        setConnected(true);
        retryDelay.current = 1000;
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setAlerts((prev) => [payload, ...prev].slice(0, 100));
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          retryTimeout = setTimeout(connect, retryDelay.current);
          retryDelay.current = Math.min(retryDelay.current * 2, 15000);
        }
      };

      socket.onerror = () => socket.close();
    };

    connect();
    return () => {
      cancelled = true;
      clearTimeout(retryTimeout);
      socket?.close();
    };
  }, [path]);

  return { alerts, connected };
}
