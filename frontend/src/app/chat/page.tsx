"use client";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { messages, isLoading, agentInfo, sendMessage } = useChat();
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)]">
      <h2 className="text-2xl font-bold mb-4">AIチャット</h2>

      {/* Agent Status */}
      {agentInfo && (
        <div className="mb-2 flex items-center gap-2">
          <Badge variant="secondary">{agentInfo.agent}</Badge>
          <span className="text-sm text-muted-foreground">{agentInfo.decision}</span>
          {isLoading && <span className="text-sm animate-pulse">処理中...</span>}
        </div>
      )}

      {/* Messages */}
      <ScrollArea className="flex-1 mb-4">
        <div className="space-y-3 pr-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <Card className={`max-w-[80%] ${msg.role === "user" ? "bg-primary text-primary-foreground" : ""}`}>
                <CardContent className="p-3">
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </CardContent>
              </Card>
            </div>
          ))}
          {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
            <div className="flex justify-start">
              <Card><CardContent className="p-3"><p className="text-sm animate-pulse">考え中...</p></CardContent></Card>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="flex gap-2">
        <Input value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) handleSend(); }}
          placeholder="メッセージを入力..." disabled={isLoading} />
        <Button onClick={handleSend} disabled={isLoading || !input.trim()}>送信</Button>
      </div>
    </div>
  );
}
