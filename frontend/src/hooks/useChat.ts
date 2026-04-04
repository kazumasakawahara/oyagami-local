"use client";
import { useCallback, useEffect, useRef, useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface AgentInfo {
  agent: string;
  decision: string;
}

function setupWsHandlers(
  ws: WebSocket,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>,
  setAgentInfo: React.Dispatch<React.SetStateAction<AgentInfo | null>>,
  currentResponseRef: React.MutableRefObject<string>,
  wsRef: React.MutableRefObject<WebSocket | null>,
) {
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "routing") {
      setAgentInfo({ agent: msg.agent, decision: msg.decision });
    } else if (msg.type === "stream") {
      currentResponseRef.current += msg.content || "";
      const text = currentResponseRef.current;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === "assistant") {
          return [...prev.slice(0, -1), { role: "assistant", content: text }];
        }
        return [...prev, { role: "assistant", content: text }];
      });
    } else if (msg.type === "done") {
      currentResponseRef.current = "";
      setIsLoading(false);
      setAgentInfo(null);
    }
  };
  ws.onclose = () => { setIsLoading(false); wsRef.current = null; };
  ws.onerror = () => { setIsLoading(false); wsRef.current = null; };
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [agentInfo, setAgentInfo] = useState<AgentInfo | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const currentResponseRef = useRef("");

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsUrl = apiBase.replace(/^http/, "ws") + "/api/chat/ws";
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => console.log("Chat WebSocket connected");
    setupWsHandlers(ws, setMessages, setIsLoading, setAgentInfo, currentResponseRef, wsRef);
    return () => { ws.close(); };
  }, []);

  const sendMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { role: "user", content }]);
    setIsLoading(true);
    currentResponseRef.current = "";

    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "message", content }));
    } else {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const wsUrl = apiBase.replace(/^http/, "ws") + "/api/chat/ws";
      const newWs = new WebSocket(wsUrl);
      wsRef.current = newWs;
      newWs.onopen = () => {
        newWs.send(JSON.stringify({ type: "message", content }));
      };
      setupWsHandlers(newWs, setMessages, setIsLoading, setAgentInfo, currentResponseRef, wsRef);
    }
  }, []);

  return { messages, isLoading, agentInfo, sendMessage };
}
