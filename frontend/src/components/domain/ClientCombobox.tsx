"use client";
import { useEffect, useMemo, useRef, useState } from "react";

interface ClientOption {
  name: string;
  kana?: string | null;
}

interface Props {
  clients: ClientOption[];
  value: string;
  onChange: (name: string) => void;
  placeholder?: string;
  className?: string;
}

// 五十音の行頭 -> その行に属するひらがな（濁点・半濁点・小書きを含む）
const KANA_ROWS: { head: string; members: string }[] = [
  { head: "あ", members: "あいうえおぁぃぅぇぉゔ" },
  { head: "か", members: "かきくけこがぎぐげご" },
  { head: "さ", members: "さしすせそざじずぜぞ" },
  { head: "た", members: "たちつてとだぢづでどっ" },
  { head: "な", members: "なにぬねの" },
  { head: "は", members: "はひふへほばびぶべぼぱぴぷぺぽ" },
  { head: "ま", members: "まみむめも" },
  { head: "や", members: "やゆよゃゅょ" },
  { head: "ら", members: "らりるれろ" },
  { head: "わ", members: "わをんゎ" },
];

/** カタカナをひらがなに正規化。 */
function toHiragana(s: string): string {
  return s.replace(/[\u30a1-\u30f6]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0x60)
  );
}

/** 読み仮名の先頭文字から五十音行（行頭文字）を返す。該当なしは null（=「他」）。 */
function rowOf(kana?: string | null): string | null {
  if (!kana) return null;
  const first = toHiragana(kana[0]);
  const row = KANA_ROWS.find((r) => r.members.includes(first));
  return row ? row.head : null;
}

type RowKey = "all" | "other" | string;

/**
 * クライアント選択ピッカー。
 * テキスト入力を持たず、「あかさたな…」のかな行チップで候補を絞り、リストからタップ選択する。
 * 入力欄がないため日本語IMEの変換候補ウィンドウと干渉しない。
 */
export function ClientCombobox({
  clients,
  value,
  onChange,
  placeholder = "選択してください",
  className,
}: Props) {
  const [open, setOpen] = useState(false);
  const [row, setRow] = useState<RowKey>("all");
  const wrapRef = useRef<HTMLDivElement>(null);

  // 外側クリックで閉じる。
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const filtered = useMemo(() => {
    if (row === "all") return clients;
    if (row === "other") return clients.filter((c) => rowOf(c.kana) === null);
    return clients.filter((c) => rowOf(c.kana) === row);
  }, [clients, row]);

  function select(name: string) {
    onChange(name);
    setOpen(false);
  }

  const chipBase = "px-2 py-0.5 rounded text-xs";
  const chip = (active: boolean) =>
    `${chipBase} ${active ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80"}`;

  return (
    <div ref={wrapRef} className={`relative ${className ?? ""}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full border rounded px-3 py-2 text-sm text-left flex items-center justify-between gap-2"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={value ? "" : "text-muted-foreground"}>{value || placeholder}</span>
        <span className="text-muted-foreground" aria-hidden>▾</span>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[16rem] rounded border bg-popover text-popover-foreground shadow-md">
          <div className="flex flex-wrap gap-1 p-2 border-b">
            <button type="button" onClick={() => setRow("all")} className={chip(row === "all")}>
              全て
            </button>
            {KANA_ROWS.map((r) => (
              <button key={r.head} type="button" onClick={() => setRow(r.head)} className={chip(row === r.head)}>
                {r.head}
              </button>
            ))}
            <button type="button" onClick={() => setRow("other")} className={chip(row === "other")}>
              他
            </button>
          </div>
          <ul className="max-h-60 overflow-auto py-1" role="listbox">
            {filtered.length === 0 ? (
              <li className="px-3 py-2 text-sm text-muted-foreground">該当なし</li>
            ) : (
              filtered.map((c) => (
                <li
                  key={c.name}
                  role="option"
                  aria-selected={c.name === value}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    select(c.name);
                  }}
                  className={`flex cursor-pointer items-center justify-between px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground ${
                    c.name === value ? "font-medium bg-accent/50" : ""
                  }`}
                >
                  <span>{c.name}</span>
                  {c.kana ? (
                    <span className="ml-2 text-xs text-muted-foreground">{c.kana}</span>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
