"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { KanaFilter } from "@/components/domain/KanaFilter";
import { api } from "@/lib/api";

export default function ClientsPage() {
  const [kana, setKana] = useState<string | null>(null);
  const { data: clients } = useQuery({
    queryKey: ["clients", kana],
    queryFn: () => api.clients.list(kana ?? undefined),
  });

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">クライアント一覧</h2>
      <KanaFilter selected={kana} onSelect={setKana} />
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名前</TableHead>
                <TableHead>年齢</TableHead>
                <TableHead>状態・障害</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {clients?.map((c) => (
                <TableRow key={c.name}>
                  <TableCell>
                    <Link href={`/clients/${encodeURIComponent(c.name)}`} className="text-primary hover:underline font-medium">
                      {c.name}
                    </Link>
                  </TableCell>
                  <TableCell>{c.age ?? "-"}</TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {c.conditions.map((cond, i) => <Badge key={i} variant="outline">{cond}</Badge>)}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!clients?.length && (
                <TableRow><TableCell colSpan={3} className="text-center text-muted-foreground">データなし</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
