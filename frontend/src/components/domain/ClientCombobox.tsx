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

/** カタカナをひらがなに正規化（読み仮名との曖昧一致用）。 */
function toHiragana(s: string): string {
  return s.replace(/[\u30a1-\u30f6]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - 0x60)
  );
}
const norm = (s: string) => toHiragana(s).toLowerCase();

/**
 * 名前直接入力＋曖昧検索のクライアント選択コンボボックス。
 * 入力文字列を name と kana（カナ正規化）の両方に部分一致させて候補を絞り込む。
 */
export function ClientCombobox({
  clients,
  value,
  onChange,
  placeholder = "名前で検索...",
  className,
}: Props) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  // 外部から value が変わった場合（フォームのリセット等）に入力欄へ反映。
  useEffect(() => {
    setQuery(value);
  }, [value]);

  const filtered = useMemo(() => {
    const q = norm(query.trim());
    if (!q) return clients;
    return clients.filter(
      (c) => norm(c.name).includes(q) || (c.kana ? norm(c.kana).includes(q) : false)
    );
  }, [clients, query]);

  // 外側クリックで閉じ、入力欄を確定済みの値に戻す。
  useEffect(() => {
    function handle(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery(value);
      }
    }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [value]);

  function select(name: string) {
    onChange(name);
    setQuery(name);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHi((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHi((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filtered[hi]) select(filtered[hi].name);
    } else if (e.key === "Escape") {
      setOpen(false);
      setQuery(value);
    }
  }

  return (
    <div ref={wrapRef} className={`relative ${className ?? ""}`}>
      <input
        type="text"
        value={query}
        placeholder={placeholder}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHi(0);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="w-full border rounded px-3 py-2 text-sm"
        role="combobox"
        aria-expanded={open}
        autoComplete="off"
      />
      {open && (
        <ul className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded border bg-popover text-popover-foreground shadow-md">
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-sm text-muted-foreground">該当なし</li>
          ) : (
            filtered.map((c, i) => (
              <li
                key={c.name}
                onMouseDown={(e) => {
                  e.preventDefault();
                  select(c.name);
                }}
                onMouseEnter={() => setHi(i)}
                className={`flex cursor-pointer items-center justify-between px-3 py-2 text-sm ${
                  i === hi ? "bg-accent text-accent-foreground" : ""
                } ${c.name === value ? "font-medium" : ""}`}
              >
                <span>{c.name}</span>
                {c.kana ? (
                  <span className="ml-2 text-xs text-muted-foreground">{c.kana}</span>
                ) : null}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
