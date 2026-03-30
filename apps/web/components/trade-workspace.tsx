"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@tradenoc/ui";
import type { TradeEntry, TradeImportResult } from "@tradenoc/types";

function buildTradePayload(formData: FormData) {
  const symbol = String(formData.get("symbol") ?? "").trim().toUpperCase();
  const tradeDate = String(formData.get("trade_date") ?? "").trim() || new Date().toISOString().slice(0, 10);
  const assetType = String(formData.get("asset_type") ?? "stock");
  const side = String(formData.get("side") ?? "long");
  const quantity = Number(String(formData.get("quantity") ?? ""));
  const entryPrice = Number(String(formData.get("entry_price") ?? ""));
  const exitPrice = Number(String(formData.get("exit_price") ?? ""));
  const pnl = Number(String(formData.get("pnl") ?? ""));
  const fees = Number(String(formData.get("fees") ?? ""));
  const notes = String(formData.get("notes") ?? "").trim() || null;
  const tags = String(formData.get("tags") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  return {
    trade_date: tradeDate,
    symbol,
    asset_type: assetType,
    side,
    quantity: Number.isFinite(quantity) ? quantity : null,
    entry_price: Number.isFinite(entryPrice) ? entryPrice : null,
    exit_price: Number.isFinite(exitPrice) ? exitPrice : null,
    pnl: Number.isFinite(pnl) ? pnl : null,
    fees: Number.isFinite(fees) ? fees : 0,
    tags,
    notes,
    source_type: "manual" as const,
  };
}

export function TradeWorkspace({ trades }: { trades: TradeEntry[] }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [tradeMessage, setTradeMessage] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<TradeImportResult | null>(null);
  const [editingTradeId, setEditingTradeId] = useState<string | null>(null);

  const editingTrade = trades.find((trade) => trade.id === editingTradeId) ?? null;

  async function handleTradeSubmit(formData: FormData) {
    setTradeMessage(null);
    const payload = buildTradePayload(formData);

    if (!payload.symbol) {
      setTradeMessage("Add a symbol before saving the trade.");
      return;
    }

    startTransition(async () => {
      const response = await fetch(editingTrade ? `/api/trades/${editingTrade.id}` : "/api/trades", {
        method: editingTrade ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setTradeMessage(data.detail ?? data.message ?? "Unable to save trade entry.");
        return;
      }

      setTradeMessage(editingTrade ? `${payload.symbol} trade updated.` : `${payload.symbol} trade saved.`);
      setEditingTradeId(null);
      router.refresh();
    });
  }

  async function handleTradeDelete(tradeId: string, symbol: string) {
    const confirmed = window.confirm(`Delete the saved ${symbol} trade?`);
    if (!confirmed) {
      return;
    }

    setTradeMessage(null);
    startTransition(async () => {
      const response = await fetch(`/api/trades/${tradeId}`, { method: "DELETE" });
      const data = (await response.json()) as { detail?: string; message?: string };
      if (!response.ok) {
        setTradeMessage(data.detail ?? data.message ?? "Unable to delete trade entry.");
        return;
      }

      if (editingTradeId === tradeId) {
        setEditingTradeId(null);
      }
      setTradeMessage(`${symbol} trade deleted.`);
      router.refresh();
    });
  }

  async function handleCsvSubmit(formData: FormData) {
    setUploadMessage(null);
    setImportResult(null);

    const file = formData.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setUploadMessage("Choose a CSV file before uploading.");
      return;
    }

    const upload = new FormData();
    upload.append("file", file);

    startTransition(async () => {
      const response = await fetch("/api/trades/upload-csv", {
        method: "POST",
        body: upload,
      });

      const data = await response.json();
      if (!response.ok) {
        setUploadMessage(data.message ?? "Unable to upload CSV.");
        return;
      }

      const result = data as TradeImportResult;
      setImportResult(result);
      setUploadMessage(`Imported ${result.imported_count} of ${result.rows_received} row(s) from ${result.file_name}.`);
      router.refresh();
    });
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-white">{editingTrade ? "Edit trade entry" : "Manual trade entry"}</h2>
            <p className="mt-2 text-sm text-slate-300">
              Capture the key execution facts that power debriefs and history.
            </p>
          </div>
          {editingTrade ? (
            <button
              type="button"
              onClick={() => setEditingTradeId(null)}
              className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60"
            >
              Cancel edit
            </button>
          ) : null}
        </div>
        <form key={editingTrade?.id ?? "new-trade"} action={handleTradeSubmit} className="mt-6 grid gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-2 text-sm text-slate-300">
              Trade date
              <input
                name="trade_date"
                type="date"
                defaultValue={editingTrade?.trade_date ?? new Date().toISOString().slice(0, 10)}
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Asset type
              <select
                name="asset_type"
                defaultValue={editingTrade?.asset_type ?? "stock"}
                className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              >
                <option value="stock">stock</option>
                <option value="option">option</option>
                <option value="other">other</option>
              </select>
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Symbol
              <input
                name="symbol"
                defaultValue={editingTrade?.symbol ?? ""}
                placeholder="AAPL"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Side
              <select
                name="side"
                defaultValue={editingTrade?.side ?? "long"}
                className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              >
                <option value="long">long</option>
                <option value="short">short</option>
                <option value="call">call</option>
                <option value="put">put</option>
                <option value="other">other</option>
              </select>
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Quantity
              <input
                name="quantity"
                type="number"
                step="0.01"
                defaultValue={editingTrade?.quantity ?? ""}
                placeholder="100"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              PnL
              <input
                name="pnl"
                type="number"
                step="0.01"
                defaultValue={editingTrade?.pnl ?? ""}
                placeholder="250"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Fees
              <input
                name="fees"
                type="number"
                step="0.01"
                defaultValue={editingTrade?.fees ?? ""}
                placeholder="2.00"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Entry price
              <input
                name="entry_price"
                type="number"
                step="0.0001"
                defaultValue={editingTrade?.entry_price ?? ""}
                placeholder="217.50"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
            <label className="grid gap-2 text-sm text-slate-300">
              Exit price
              <input
                name="exit_price"
                type="number"
                step="0.0001"
                defaultValue={editingTrade?.exit_price ?? ""}
                placeholder="220.10"
                className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
              />
            </label>
          </div>
          <label className="grid gap-2 text-sm text-slate-300">
            Tags
            <input
              name="tags"
              defaultValue={editingTrade?.tags.join(", ") ?? ""}
              placeholder="opening-range, earnings-follow-through"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            Notes
            <textarea
              name="notes"
              rows={4}
              defaultValue={editingTrade?.notes ?? ""}
              placeholder="Respected planned risk and exit."
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-slate-400">
              {tradeMessage ?? "Manual entries save immediately through the trade API."}
            </p>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-full bg-cyan-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-cyan-200 disabled:opacity-60"
            >
              {isPending ? "Saving..." : editingTrade ? "Update trade" : "Save trade"}
            </button>
          </div>
        </form>
      </Card>

      <Card>
        <h2 className="text-lg font-medium text-white">CSV import</h2>
        <p className="mt-2 text-sm text-slate-300">
          Upload a broker export into the normalized import parser. Valid rows are persisted immediately and rejected rows are reported back.
        </p>
        <form action={handleCsvSubmit} className="mt-6 grid gap-4">
          <label className="grid gap-2 text-sm text-slate-300">
            CSV file
            <input
              name="file"
              type="file"
              accept=".csv,text/csv"
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-white file:mr-4 file:rounded-full file:border-0 file:bg-emerald-300 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-950"
            />
          </label>
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-slate-400">
              {uploadMessage ??
                "Supported columns include date/trade_date, symbol/ticker, side/action, quantity/qty, entry/exit prices, pnl, fees, tags, and notes."}
            </p>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-full bg-emerald-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-emerald-200 disabled:opacity-60"
            >
              {isPending ? "Uploading..." : "Upload CSV"}
            </button>
          </div>
        </form>
        {importResult ? (
          <div className="mt-6 grid gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-slate-300">
              <p className="font-medium text-white">Import summary</p>
              <p className="mt-2">
                {importResult.imported_count} imported, {importResult.rejected_count} rejected, {importResult.rows_received} data row
                {importResult.rows_received === 1 ? "" : "s"} processed.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-slate-300">
              <p className="font-medium text-white">Preview</p>
              <ul className="mt-3 space-y-2">
                {importResult.preview.length > 0 ? (
                  importResult.preview.map((row) => (
                    <li key={`${row.row_number}-${row.trade.symbol}`}>
                      Row {row.row_number}: {row.trade.trade_date} {row.trade.symbol} {row.trade.side} qty {row.trade.quantity ?? "n/a"}
                    </li>
                  ))
                ) : (
                  <li>No valid rows were imported.</li>
                )}
              </ul>
            </div>
            {importResult.errors.length > 0 ? (
              <div className="rounded-2xl border border-rose-400/20 bg-rose-400/10 px-4 py-4 text-sm text-rose-100">
                <p className="font-medium text-white">Rejected rows</p>
                <ul className="mt-3 space-y-2">
                  {importResult.errors.map((error) => (
                    <li key={`${error.row_number}-${error.message}`}>
                      Row {error.row_number}: {error.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4 text-sm text-slate-300">
          <p className="font-medium text-white">Saved trade count</p>
          <p className="mt-2">{trades.length} trade {trades.length === 1 ? "entry" : "entries"} available for debriefs and history.</p>
        </div>
      </Card>

      <Card className="xl:col-span-2">
        <h2 className="text-lg font-medium text-white">Saved trades</h2>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          {trades.length > 0 ? (
            trades.map((trade) => (
              <li key={trade.id} className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-white">
                      {trade.trade_date} | {trade.symbol} | {trade.side}
                    </p>
                    <p className="mt-1 text-slate-400">
                      Qty {trade.quantity ?? "n/a"} | Entry {trade.entry_price ?? "n/a"} | Exit {trade.exit_price ?? "n/a"} | PnL {trade.pnl ?? "n/a"}
                    </p>
                    <p className="mt-2 text-slate-400">{trade.notes ?? "No note yet."}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setEditingTradeId(trade.id)}
                      className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white transition hover:border-cyan-300/60"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleTradeDelete(trade.id, trade.symbol)}
                      className="rounded-full border border-rose-400/30 px-4 py-2 text-sm font-medium text-rose-100 transition hover:border-rose-300/60"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))
          ) : (
            <li className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-4">No saved trades yet.</li>
          )}
        </ul>
      </Card>
    </div>
  );
}
