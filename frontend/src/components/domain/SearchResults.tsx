"use client";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SemanticSearchResult } from "@/lib/types";

interface Props {
  results: SemanticSearchResult[];
}

export function SearchResults({ results }: Props) {
  if (!results.length)
    return <p className="text-sm text-muted-foreground">結果なし</p>;
  return (
    <div className="space-y-3">
      {results.map((r, i) => (
        <Card key={i}>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between mb-2">
              <Badge variant="outline">{r.node_label}</Badge>
              <span className="text-xs text-muted-foreground">
                スコア: {(r.score * 100).toFixed(1)}%
              </span>
            </div>
            <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
              {JSON.stringify(r.properties, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
