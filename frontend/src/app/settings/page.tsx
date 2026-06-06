"use client";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";

const MODELS = {
  resident: [
    { name: "gemma4:12b", size: "6.7GB", role: "Coordinator / Validator" },
    { name: "nomic-embed-text", size: "0.3GB", role: "Embedding" },
  ],
  exclusive: [
    { name: "deepseek-r1:70b", size: "42GB", role: "Intake（テキスト抽出）" },
    { name: "llama4:latest", size: "67GB", role: "Analyst（分析）" },
    { name: "qwen3-coder:30b", size: "18GB", role: "CypherGen（クエリ生成）" },
  ],
};

export default function SettingsPage() {
  const { data: status, refetch } = useQuery({
    queryKey: ["system-status"],
    queryFn: api.system.status,
    refetchInterval: 5000,
  });

  const loadedSet = new Set(status?.loaded_models ?? []);
  const totalLoaded = MODELS.resident.filter((m) => loadedSet.has(m.name)).reduce((s, m) => s + parseFloat(m.size), 0)
    + MODELS.exclusive.filter((m) => loadedSet.has(m.name)).reduce((s, m) => s + parseFloat(m.size), 0);

  const handleLoad = async (name: string) => { await api.system.loadModel(name); refetch(); };
  const handleUnload = async (name: string) => { await api.system.unloadModel(name); refetch(); };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">LLM設定</h2>

      {/* Connection Status */}
      <div className="flex gap-4">
        <Badge variant={status?.ollama_available ? "default" : "destructive"}>
          Ollama: {status?.ollama_available ? "接続中" : "未接続"}
        </Badge>
        <Badge variant={status?.neo4j_available ? "default" : "destructive"}>
          Neo4j: {status?.neo4j_available ? "接続中" : "未接続"}
        </Badge>
      </div>

      {/* Memory */}
      <Card>
        <CardHeader><CardTitle className="text-base">メモリ使用状況</CardTitle></CardHeader>
        <CardContent>
          <Progress value={(totalLoaded / 128) * 100} className="mb-2" />
          <p className="text-sm text-muted-foreground">{totalLoaded.toFixed(1)} / 128 GB</p>
        </CardContent>
      </Card>

      {/* Resident Models */}
      <Card>
        <CardHeader><CardTitle className="text-base">常駐モデル</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {MODELS.resident.map((m) => (
              <li key={m.name} className="flex items-center justify-between text-sm">
                <div>
                  <Badge variant={loadedSet.has(m.name) ? "default" : "outline"} className="mr-2">
                    {loadedSet.has(m.name) ? "●" : "○"}
                  </Badge>
                  {m.name} <span className="text-muted-foreground">({m.size})</span>
                </div>
                <span className="text-muted-foreground">{m.role}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Exclusive Models */}
      <Card>
        <CardHeader><CardTitle className="text-base">オンデマンドモデル</CardTitle></CardHeader>
        <CardContent>
          <ul className="space-y-3">
            {MODELS.exclusive.map((m) => (
              <li key={m.name} className="flex items-center justify-between text-sm">
                <div>
                  <Badge variant={loadedSet.has(m.name) ? "default" : "outline"} className="mr-2">
                    {loadedSet.has(m.name) ? "●" : "○"}
                  </Badge>
                  {m.name} <span className="text-muted-foreground">({m.size})</span>
                  <span className="text-muted-foreground ml-2">{m.role}</span>
                </div>
                {loadedSet.has(m.name) ? (
                  <Button size="sm" variant="outline" onClick={() => handleUnload(m.name)}>アンロード</Button>
                ) : (
                  <Button size="sm" onClick={() => handleLoad(m.name)}>ロード</Button>
                )}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
