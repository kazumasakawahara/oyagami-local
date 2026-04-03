"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { ExtractedGraph } from "@/lib/types";

export default function NarrativePage() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [text, setText] = useState("");
  const [extractedData, setExtractedData] = useState<ExtractedGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleExtract = async () => {
    setLoading(true);
    try {
      const data = await api.narratives.extract(text) as ExtractedGraph | null;
      if (data) {
        setExtractedData(data);
        setStep(2);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!extractedData) return;
    setLoading(true);
    try {
      const res = await api.narratives.register(extractedData) as any;
      setResult(res.status === "success"
        ? `登録完了: ${res.registered_count}件のノードを登録しました。`
        : `エラー: ${res.message}`);
      setStep(3);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h2 className="text-2xl font-bold">ナラティブ入力</h2>

      {/* Progress */}
      <div className="flex gap-2 items-center">
        {[1, 2, 3].map((s) => (
          <div key={s} className={`flex items-center gap-2`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm ${step >= s ? "bg-primary text-primary-foreground" : "bg-muted"}`}>{s}</div>
            <span className="text-sm">{s === 1 ? "入力" : s === 2 ? "確認" : "完了"}</span>
            {s < 3 && <div className="w-8 h-px bg-border" />}
          </div>
        ))}
      </div>

      {/* Step 1: Input */}
      {step === 1 && (
        <Card>
          <CardHeader><CardTitle>テキスト入力</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <Textarea placeholder="支援記録や面談メモをここに入力してください..." value={text} onChange={(e) => setText(e.target.value)} rows={10} />
            <Button onClick={handleExtract} disabled={!text.trim() || loading}>
              {loading ? "抽出中..." : "AI抽出を実行"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Preview */}
      {step === 2 && extractedData && (
        <Card>
          <CardHeader><CardTitle>抽出プレビュー</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">ノード {extractedData.nodes.length}件 / リレーション {extractedData.relationships.length}件</p>
            <div className="space-y-2">
              {extractedData.nodes.map((node, i) => (
                <div key={i} className={`border rounded p-3 ${node.label === "NgAction" ? "border-red-500" : ""}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={node.label === "NgAction" ? "destructive" : "outline"}>{node.label}</Badge>
                    <span className="text-xs text-muted-foreground">{node.temp_id}</span>
                  </div>
                  <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">{JSON.stringify(node.properties, null, 2)}</pre>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(1)}>戻る</Button>
              <Button onClick={handleRegister} disabled={loading}>{loading ? "登録中..." : "確認して登録"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Done */}
      {step === 3 && (
        <Card>
          <CardContent className="pt-6 text-center space-y-4">
            <p className="text-lg">{result}</p>
            <Button onClick={() => { setStep(1); setText(""); setExtractedData(null); setResult(null); }}>
              新しい入力を開始
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
