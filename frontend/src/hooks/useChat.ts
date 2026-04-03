"use client";
import { useCallback, useRef, useState } from "react";
import type { ChatMessage } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [agentInfo, setAgentInfo] = useState<{ agent: string; decision: string } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket("ws://localhost:8000/api/chat/ws");
    wsRef.current = ws;
    let currentResponse = "";

    ws.onmessage = (event) => {
      const msg: ChatMessage = JSON.parse(event.data);
      if (msg.type === "routing") {
        setAgentInfo({ agent: msg.agent!, decision: msg.decision! });
      } else if (msg.type === "stream") {
        currentResponse += msg.content || "";
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            return [...updated.slice(0, -1), { ...last, content: currentResponse }];
          }
          return [...updated, { role: "assistant", content: currentResponse }];
        });
      } else if (msg.type === "done") {
        currentResponse = "";
        setIsLoading(false);
        setAgentInfo(null);
      }
    };
    ws.onclose = () => { setIsLoading(false); };
  }, []);

  const sendMessage = useCallback((content: string) => {
    connect();
    setTimeout(() => {
      setMessages((prev) => [...prev, { role: "user", content }]);
      setIsLoading(true);
      wsRef.current?.send(JSON.stringify({ type: "message", content }));
    }, 100);
  }, [connect]);

  return { messages, isLoading, agentInfo, sendMessage };
}
