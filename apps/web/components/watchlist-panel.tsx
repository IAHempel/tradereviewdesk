"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@tradenoc/ui";
import type { Watchlist } from "@tradenoc/types";

import { getSymbolMetadata, symbolCatalog, type SymbolAssetType } from "@/lib/symbol-catalog";

const assetTypeFilters = ["all", "stock", "etf", "crypto"] as const;
const sortOptions = ["manual", "symbol", "company", "assetType", "category"] as const;
const sortLabels: Record<(typeof sortOptions)[number], string> = {
  manual: "Manual order",
  symbol: "Ticker",
  company: "Company",
  assetType: "Asset type",
  category: "Category",
};

type WatchlistRow = {
  id: string;
  symbol: string;
  notes: string | null;
  display_order: number;
  company: string;
  assetType: SymbolAssetType;
  category: string;
};

async function readClientPayload(response: Response): Promise<{ detail?: string; message?: string; id?: string }> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as { detail?: string; message?: string; id?: string };
  }

  const text = await response.text();
  return { message: text || "The request returned an unexpected response." };
}

function formatAssetType(assetType: SymbolAssetType) {
  return assetType === "etf" ? "ETF" : assetType === "crypto" ? "Crypto" : "Stock";
}

export function WatchlistPanel({ watchlists }: { watchlists: Watchlist[] }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null);
  const [symbolMessage, setSymbolMessage] = useState<string | null>(null);
  const [editingSymbolId, setEditingSymbolId] = useState<string | null>(null);
  const [selectedWatchlistId, setSelectedWatchlistId] = useState<string | null>(
    watchlists.find((watchlist) => watchlist.is_default)?.id ?? watchlists[0]?.id ?? null,
  );
  const [newWatchlistName, setNewWatchlistName] = useState("");
  const [symbolQuery, setSymbolQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [watchlistSearch, setWatchlistSearch] = useState("");
  const [assetTypeFilter, setAssetTypeFilter] = useState<(typeof assetTypeFilters)[number]>("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [sortOption, setSortOption] = useState<(typeof sortOptions)[number]>("manual");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const defaultWatchlist = watchlists.find((watchlist) => watchlist.is_default) ?? watchlists[0] ?? null;
  const activeWatchlist = watchlists.find((watchlist) => watchlist.id === selectedWatchlistId) ?? defaultWatchlist;
  const editingSymbol = activeWatchlist?.symbols.find((symbol) => symbol.id === editingSymbolId) ?? null;
  const normalizedSymbolQuery = symbolQuery.trim().toLowerCase();
  const suggestions =
    normalizedSymbolQuery.length === 0
      ? []
      : symbolCatalog
          .filter(
            (item) =>
              item.symbol.toLowerCase().includes(normalizedSymbolQuery) ||
              item.company.toLowerCase().includes(normalizedSymbolQuery),
          )
          .slice(0, 10);

  const rows: WatchlistRow[] = (activeWatchlist?.symbols ?? []).map((symbol) => {
    const metadata = getSymbolMetadata(symbol.symbol);
    return {
      ...symbol,
      company: metadata?.company ?? "Custom symbol",
      assetType: metadata?.assetType ?? "stock",
      category: metadata?.category ?? "Custom / Unclassified",
    };
  });
  const categoryOptions = Array.from(new Set(rows.map((item) => item.category))).sort((left, right) => left.localeCompare(right));
  const searchTerm = watchlistSearch.trim().toLowerCase();
  const visibleRows = rows
    .filter((item) => (assetTypeFilter === "all" ? true : item.assetType === assetTypeFilter))
    .filter((item) => (categoryFilter === "all" ? true : item.category === categoryFilter))
    .filter((item) =>
      searchTerm ? [item.symbol, item.company, item.category, item.notes ?? ""].some((value) => value.toLowerCase().includes(searchTerm)) : true,
    )
    .sort((left, right) => {
      const direction = sortDirection === "asc" ? 1 : -1;
      if (sortOption === "manual") {
        return (left.display_order - right.display_order) * direction;
      }
      const leftValue =
        sortOption === "symbol" ? left.symbol : sortOption === "company" ? left.company : sortOption === "assetType" ? left.assetType : left.category;
      const rightValue =
        sortOption === "symbol" ? right.symbol : sortOption === "company" ? right.company : sortOption === "assetType" ? right.assetType : right.category;
      return leftValue.localeCompare(rightValue) * direction;
    });

  async function addSymbol(symbolInput: string, notes: string | null = null) {
    setSymbolMessage(null);
    if (!activeWatchlist) {
      setSymbolMessage("Create a watchlist before adding symbols.");
      return;
    }

    const trimmed = symbolInput.trim();
    const matched =
      symbolCatalog.find((item) => item.symbol.toLowerCase() === trimmed.toLowerCase()) ??
      symbolCatalog.find((item) => item.company.toLowerCase() === trimmed.toLowerCase());
    const symbol = (matched?.symbol ?? trimmed).toUpperCase();

    if (!symbol) {
      setSymbolMessage("Enter or select a symbol before adding it.");
      return;
    }
    if (symbol.includes(" ")) {
      setSymbolMessage("Select a suggested ticker or enter a valid symbol like AAPL.");
      return;
    }
    if (activeWatchlist.symbols.some((item) => item.symbol === symbol)) {
      setSymbolMessage(`${symbol} is already on ${activeWatchlist.name}.`);
      return;
    }

    startTransition(async () => {
      const response = await fetch(`/api/watchlists/${activeWatchlist.id}/symbols`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, notes: notes?.trim() || null }),
      });
      const data = await readClientPayload(response);
      if (!response.ok) {
        setSymbolMessage(data.detail ?? data.message ?? "Unable to add symbol right now.");
        return;
      }
      setSymbolQuery("");
      setShowSuggestions(false);
      setSymbolMessage(`${symbol} added to ${activeWatchlist.name}.`);
      router.refresh();
    });
  }

  async function handleWatchlistCreate(formData: FormData) {
    setWatchlistMessage(null);
    const name = String(formData.get("watchlist_name") ?? "").trim();
    if (!name) {
      setWatchlistMessage("Enter a name for the new watchlist.");
      return;
    }

    startTransition(async () => {
      const response = await fetch("/api/watchlists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, is_default: formData.get("watchlist_is_default") === "on" }),
      });
      const data = await readClientPayload(response);
      if (!response.ok) {
        setWatchlistMessage(data.detail ?? data.message ?? "Unable to create watchlist right now.");
        return;
      }
      setNewWatchlistName("");
      setSelectedWatchlistId(data.id ?? null);
      setWatchlistMessage(`Created ${name}.`);
      router.refresh();
    });
  }

  async function handleWatchlistUpdate(formData: FormData) {
    setWatchlistMessage(null);
    if (!activeWatchlist) {
      return;
    }

    const payload = { name: String(formData.get("name") ?? "").trim(), is_default: formData.get("is_default") === "on" };
    if (!payload.name) {
      setWatchlistMessage("Watchlist name cannot be empty.");
      return;
    }

    startTransition(async () => {
      const response = await fetch(`/api/watchlists/${activeWatchlist.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await readClientPayload(response);
      if (!response.ok) {
        setWatchlistMessage(data.detail ?? data.message ?? "Unable to update watchlist.");
        return;
      }
      setWatchlistMessage(`Updated ${payload.name}.`);
      router.refresh();
    });
  }

  async function handleWatchlistDelete() {
    setWatchlistMessage(null);
    if (!activeWatchlist || !window.confirm(`Delete ${activeWatchlist.name}? This will remove its saved symbols and notes.`)) {
      return;
    }

    startTransition(async () => {
      const response = await fetch(`/api/watchlists/${activeWatchlist.id}`, { method: "DELETE" });
      const data = await readClientPayload(response);
      if (!response.ok) {
        setWatchlistMessage(data.detail ?? data.message ?? "Unable to delete watchlist.");
        return;
      }
      const fallback = watchlists.find((watchlist) => watchlist.id !== activeWatchlist.id) ?? null;
      setSelectedWatchlistId(fallback?.id ?? null);
      setWatchlistMessage(`${activeWatchlist.name} deleted.`);
      router.refresh();
    });
  }

  async function handleSymbolSubmit(formData: FormData) {
    await addSymbol(String(formData.get("symbol") ?? ""), String(formData.get("notes") ?? "").trim() || null);
  }

  async function handleSymbolUpdate(formData: FormData) {
    if (!activeWatchlist || !editingSymbol) {
      return;
    }
    setSymbolMessage(null);
    startTransition(async () => {
      const response = await fetch(`/api/watchlists/${activeWatchlist.id}/symbols/${editingSymbol.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: String(formData.get("notes") ?? "").trim() || null }),
      });
      const data = await readClientPayload(response);
      if (!response.ok) {
        setSymbolMessage(data.detail ?? data.message ?? "Unable to update symbol notes.");
        return;
      }
      setEditingSymbolId(null);
      setSymbolMessage(`${editingSymbol.symbol} updated.`);
      router.refresh();
    });
  }

  async function handleSymbolDelete(symbolId: string, symbol: string) {
    if (!activeWatchlist || !window.confirm(`Delete ${symbol} from ${activeWatchlist.name}?`)) {
      return;
    }
    setSymbolMessage(null);
    startTransition(async () => {
      const response = await fetch(`/api/watchlists/${activeWatchlist.id}/symbols/${symbolId}`, { method: "DELETE" });
      const data = await readClientPayload(response);
      if (!response.ok) {
        setSymbolMessage(data.detail ?? data.message ?? "Unable to delete symbol right now.");
        return;
      }
      if (editingSymbolId === symbolId) {
        setEditingSymbolId(null);
      }
      setSymbolMessage(`${symbol} removed from ${activeWatchlist.name}.`);
      router.refresh();
    });
  }

  return (
    <Card>
      <div className="mb-6">
        <h2 className="text-lg font-medium text-white">Watchlist workspace</h2>
        <p className="mt-2 text-sm text-slate-300">Create multiple lists, switch between them, and manage symbols with filters for stocks, ETFs, crypto, and categories.</p>
      </div>

      <form action={handleWatchlistCreate} className="grid gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
        <label className="grid gap-2 text-sm text-slate-300">
          New watchlist name
          <input name="watchlist_name" value={newWatchlistName} onChange={(event) => setNewWatchlistName(event.target.value)} placeholder="Momentum Leaders" className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-emerald-300/60" />
        </label>
        <label className="flex items-center gap-3 text-sm text-slate-300">
          <input type="checkbox" name="watchlist_is_default" className="size-4 accent-emerald-300" />
          Make this the default watchlist
        </label>
        <button type="submit" disabled={isPending} className="inline-flex items-center justify-center rounded-full bg-emerald-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-60">
          {isPending ? "Creating..." : "Create watchlist"}
        </button>
      </form>

      <div className="mt-6 flex flex-wrap gap-3">
        {watchlists.map((watchlist) => (
          <button key={watchlist.id} type="button" onClick={() => { setSelectedWatchlistId(watchlist.id); setEditingSymbolId(null); }} className={`rounded-2xl border px-4 py-3 text-left transition ${activeWatchlist?.id === watchlist.id ? "border-cyan-300/60 bg-cyan-300/15 text-white" : "border-white/10 bg-white/[0.03] text-slate-300 hover:border-cyan-300/30"}`}>
            <div className="flex items-center gap-2">
              <span className="font-medium">{watchlist.name}</span>
              {watchlist.is_default ? <span className="rounded-full border border-emerald-300/30 bg-emerald-300/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-emerald-200">Default</span> : null}
            </div>
            <p className="mt-1 text-xs text-slate-400">{watchlist.symbols.length} saved</p>
          </button>
        ))}
      </div>

      {activeWatchlist ? (
        <>
          <form key={activeWatchlist.id} action={handleWatchlistUpdate} className="mt-6 grid gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm font-medium text-white">Manage active watchlist</p>
              <button type="button" onClick={handleWatchlistDelete} disabled={isPending} className="rounded-full border border-rose-400/30 px-4 py-2 text-sm font-medium text-rose-100 transition hover:border-rose-300/60 disabled:cursor-not-allowed disabled:opacity-60">Delete list</button>
            </div>
            <label className="grid gap-2 text-sm text-slate-300">
              Watchlist name
              <input name="name" defaultValue={activeWatchlist.name} className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60" />
            </label>
            <label className="flex items-center gap-3 text-sm text-slate-300">
              <input type="checkbox" name="is_default" defaultChecked={activeWatchlist.is_default} className="size-4 accent-cyan-300" />
              Use this as the default watchlist
            </label>
            <button type="submit" disabled={isPending} className="inline-flex items-center justify-center rounded-full border border-cyan-300/40 px-5 py-3 text-sm font-medium text-white transition hover:border-cyan-300/70 disabled:cursor-not-allowed disabled:opacity-60">
              {isPending ? "Saving..." : "Save watchlist changes"}
            </button>
          </form>

          <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-white">Add symbols to {activeWatchlist.name}</p>
                <p className="mt-1 text-sm text-slate-400">Click Add on a suggestion for quick entry, or attach a note before saving.</p>
              </div>
              <div className="rounded-full border border-white/10 bg-slate-950/60 px-4 py-2 text-xs uppercase tracking-[0.18em] text-slate-300">{visibleRows.length}/{rows.length} visible</div>
            </div>

            <form action={handleSymbolSubmit} className="mt-4 grid gap-4">
              <label className="grid gap-2 text-sm text-slate-300">
                Symbol or company
                <div className="relative">
                  <input
                    name="symbol"
                    value={symbolQuery}
                    onChange={(event) => { setSymbolQuery(event.target.value); setShowSuggestions(true); }}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => { window.setTimeout(() => setShowSuggestions(false), 120); }}
                    placeholder="Type AAPL, Apple, BTC, or Bitcoin"
                    autoComplete="off"
                    className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-emerald-300/60"
                  />
                  {showSuggestions && suggestions.length > 0 ? (
                    <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-white/10 bg-slate-950 shadow-[0_18px_60px_rgba(15,23,42,0.55)]">
                      {suggestions.map((item) => {
                        const alreadySaved = activeWatchlist.symbols.some((symbol) => symbol.symbol === item.symbol);
                        return (
                          <div key={item.symbol} className="flex items-center justify-between gap-3 border-b border-white/5 px-4 py-3 last:border-b-0">
                            <div>
                              <p className="font-medium text-white">{item.symbol}</p>
                              <p className="text-sm text-slate-400">{item.company} | {formatAssetType(item.assetType)} | {item.category}</p>
                            </div>
                            <button type="button" onMouseDown={(event) => { event.preventDefault(); void addSymbol(item.symbol); }} disabled={isPending || alreadySaved} className="rounded-full bg-emerald-300 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-60">
                              {alreadySaved ? "Added" : "Add"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              </label>
              <p className="text-xs text-slate-400">Search by ticker or company name. You can also submit a custom ticker directly.</p>
              <label className="grid gap-2 text-sm text-slate-300">
                Note
                <input name="notes" placeholder="Why this belongs on the list today" className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-emerald-300/60" />
              </label>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <p className="text-sm text-slate-400">{symbolMessage ?? "Add symbols, then sort and filter them below."}</p>
                <button type="submit" disabled={isPending} className="rounded-full bg-emerald-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-60">
                  {isPending ? "Saving..." : "Add selected symbol"}
                </button>
              </div>
            </form>
          </div>

          <div className="mt-6 grid gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="grid gap-2 text-sm text-slate-300">
              Search within list
              <input value={watchlistSearch} onChange={(event) => setWatchlistSearch(event.target.value)} placeholder="Ticker, company, note" className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60" />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Asset type
              <select value={assetTypeFilter} onChange={(event) => setAssetTypeFilter(event.target.value as (typeof assetTypeFilters)[number])} className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60">
                {assetTypeFilters.map((item) => <option key={item} value={item}>{item === "all" ? "All asset types" : formatAssetType(item)}</option>)}
              </select>
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Category
              <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60">
                <option value="all">All categories</option>
                {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Sort
              <div className="flex gap-2">
                <select value={sortOption} onChange={(event) => setSortOption(event.target.value as (typeof sortOptions)[number])} className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60">
                  {sortOptions.map((item) => <option key={item} value={item}>{sortLabels[item]}</option>)}
                </select>
                <button type="button" onClick={() => setSortDirection((current) => current === "asc" ? "desc" : "asc")} className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-medium text-white transition hover:border-cyan-300/60">{sortDirection === "asc" ? "Asc" : "Desc"}</button>
              </div>
            </label>
          </div>

          {editingSymbol ? (
            <form key={editingSymbol.id} action={handleSymbolUpdate} className="mt-6 grid gap-4 rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium text-white">Edit note for {editingSymbol.symbol}</p>
                <button type="button" onClick={() => setEditingSymbolId(null)} className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60">Cancel</button>
              </div>
              <label className="grid gap-2 text-sm text-slate-300">
                Note
                <input name="notes" defaultValue={editingSymbol.notes ?? ""} placeholder="High relative volume into earnings follow-through" className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60" />
              </label>
              <div className="flex justify-end">
                <button type="submit" disabled={isPending} className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60">{isPending ? "Saving..." : "Update note"}</button>
              </div>
            </form>
          ) : null}

          <ul className="mt-6 space-y-3 text-sm text-slate-300">
            {visibleRows.length === 0 ? (
              <li className="rounded-2xl border border-dashed border-white/15 px-4 py-5 text-slate-400">No symbols match the current filters for {activeWatchlist.name}.</li>
            ) : (
              visibleRows.map((item) => (
                <li key={item.id} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-white">{item.symbol}</p>
                        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-slate-300">{formatAssetType(item.assetType)}</span>
                        <span className="rounded-full border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-slate-300">{item.category}</span>
                      </div>
                      <p className="mt-1 text-slate-300">{item.company}</p>
                      <p className="mt-2 text-slate-400">{item.notes ?? "No note yet."}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button type="button" onClick={() => setEditingSymbolId(item.id)} className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-emerald-300/60">Edit note</button>
                      <button type="button" onClick={() => handleSymbolDelete(item.id, item.symbol)} className="rounded-full border border-rose-400/30 px-4 py-2 text-sm font-medium text-rose-100 transition hover:border-rose-300/60">Delete</button>
                    </div>
                  </div>
                </li>
              ))
            )}
          </ul>
        </>
      ) : (
        <div className="mt-6 rounded-2xl border border-dashed border-white/15 px-4 py-5 text-sm text-slate-400">Create your first watchlist to start adding symbols, categories, and notes.</div>
      )}

      <p className="mt-6 text-sm text-slate-400">
        {watchlistMessage ?? "Watchlists can be created, renamed, marked as default, filtered by asset type or category, and cleaned up from this workspace."}
      </p>
    </Card>
  );
}
