"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";

import type { DeskConfig, DeskLiveSession, DeskLiveStatus } from "@tradenoc/types";
import { Card } from "@tradenoc/ui";
import { StatePanel } from "@/components/state-panels";
import { formatMoney, formatSignedMoney } from "@/lib/desk";

const POLL_MS = 20_000;
export const LIVE_ACTIVE: DeskLiveStatus[] = ["scheduled", "running", "awaiting_decision", "stopping"];

const STATUS_COPY: Record<DeskLiveStatus, { label: string; tone: string }> = {
  scheduled: { label: "Waiting for the open", tone: "border-white/15 bg-white/5 text-slate-200" },
  running: { label: "Live", tone: "border-emerald-300/40 bg-emerald-400/10 text-emerald-100" },
  awaiting_decision: { label: "Waiting on you", tone: "border-amber-300/50 bg-amber-400/10 text-amber-100" },
  stopping: { label: "Stopping", tone: "border-rose-300/40 bg-rose-400/10 text-rose-100" },
  stopped: { label: "Stopped", tone: "border-white/15 bg-white/5 text-slate-300" },
  closed: { label: "Closed", tone: "border-white/15 bg-white/5 text-slate-300" },
  error: { label: "Needs attention", tone: "border-rose-300/40 bg-rose-400/10 text-rose-100" },
};

const etTime = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", timeZone: "America/New_York" });

export function formatEt(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : `${etTime.format(date)} ET`;
}

async function readJson(response: Response): Promise<{ data: unknown; message: string | null }> {
  const data = (await response.json().catch(() => null)) as { detail?: unknown; message?: string } | null;
  if (response.ok) {
    return { data, message: null };
  }
  const detail = data?.detail;
  const message = Array.isArray(detail)
    ? detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("; ")
    : typeof detail === "string"
      ? detail
      : (data?.message ?? "The live desk could not be reached.");
  return { data: null, message };
}

/** Holds the live session, polls while it is active, and exposes start/decide/stop. */
export function useLiveSession(initial: DeskLiveSession | null) {
  const [live, setLive] = useState<DeskLiveSession | null>(initial);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const active = live !== null && LIVE_ACTIVE.includes(live.status);

  const refresh = useCallback(async () => {
    const response = await fetch("/api/desk/live", { cache: "no-store" });
    const { data, message } = await readJson(response);
    if (message) {
      setError(message);
      return;
    }
    setLive(data as DeskLiveSession | null);
  }, []);

  useEffect(() => {
    if (!active) {
      return;
    }
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [active, refresh]);

  async function send(url: string, body: unknown) {
    setPending(true);
    setError(null);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const { data, message } = await readJson(response);
      if (message) {
        setError(message);
        return;
      }
      setLive(data as DeskLiveSession);
    } catch {
      setError("The live desk could not be reached.");
    } finally {
      setPending(false);
    }
  }

  return {
    live,
    active,
    pending,
    error,
    refresh,
    start: (config: DeskConfig, notifyUrl: string) => send("/api/desk/live", { ...config, notify_url: notifyUrl || null }),
    decide: (checkpoint: number, decision: "continue" | "stop") =>
      live ? send(`/api/desk/live/${live.id}/decision`, { checkpoint, decision }) : Promise.resolve(),
    stop: () => (live ? send(`/api/desk/live/${live.id}/stop`, {}) : Promise.resolve()),
  };
}

/** Optional OS-level alerts while the tab is open but in the background. */
function useBrowserAlerts(live: DeskLiveSession | null) {
  const [enabled, setEnabled] = useState(false);
  // Decided after mount so the server render and the first browser render match.
  const [supported, setSupported] = useState(false);
  const announced = useRef<string | null>(null);

  useEffect(() => {
    try {
      setSupported(typeof Notification !== "undefined");
      setEnabled(typeof Notification !== "undefined" && Notification.permission === "granted");
    } catch {
      setEnabled(false);
    }
  }, []);

  useEffect(() => {
    const checkpoint = live?.open_checkpoint;
    if (!enabled || !checkpoint || !live) {
      return;
    }
    const key = `${live.id}-${checkpoint.index}`;
    if (announced.current === key || document.visibilityState === "visible") {
      announced.current = key;
      return;
    }
    announced.current = key;
    try {
      new Notification("Paper desk: keep running?", { body: checkpoint.message });
    } catch {
      // Some browsers only allow notifications from a service worker; the in-page prompt still shows.
    }
  }, [enabled, live]);

  async function enable() {
    try {
      setEnabled((await Notification.requestPermission()) === "granted");
    } catch {
      setEnabled(false);
    }
  }

  return { enabled, enable, supported };
}

export function LiveControl({
  live,
  available,
  config,
  session,
  viewingLive,
  onView,
}: {
  live: DeskLiveSession | null;
  available: boolean;
  config: DeskConfig;
  session: ReturnType<typeof useLiveSession>;
  viewingLive: boolean;
  onView: () => void;
}) {
  const [notifyUrl, setNotifyUrl] = useState("");
  const alerts = useBrowserAlerts(live);
  const status = live ? STATUS_COPY[live.status] : null;
  const checkpoint = live?.open_checkpoint ?? null;
  const lastEquity = live?.result?.frames.at(-1)?.equity ?? null;

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold text-white">
            Live paper session
            {status ? <span className={clsx("rounded-full border px-2.5 py-0.5 text-[11px] font-semibold", status.tone)}>{status.label}</span> : null}
          </h2>
          <p className="mt-1 max-w-2xl text-xs text-slate-400">
            Runs today&apos;s market bar by bar from Alpaca&apos;s free IEX feed with paper fills. Each milestone and a drawdown level
            pause new entries until you choose to keep running. Nothing is ever sent to a broker.
          </p>
        </div>
        {live && session.active ? (
          <div className="flex flex-wrap gap-2">
            {!viewingLive ? (
              <button type="button" onClick={onView} className="rounded-full border border-white/15 px-4 py-2 text-sm text-white hover:border-cyan-300/60">
                Show live desk
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => void session.stop()}
              disabled={session.pending || live.status === "stopping"}
              className="rounded-full border border-rose-300/40 px-4 py-2 text-sm text-rose-100 transition hover:bg-rose-400/10 disabled:opacity-50"
            >
              Stop for today
            </button>
          </div>
        ) : null}
      </div>

      {checkpoint && live?.status === "awaiting_decision" ? (
        <div className="mt-4 rounded-2xl border border-amber-300/40 bg-amber-400/10 p-4" role="alert">
          <p className="text-sm font-semibold text-white">
            Checkpoint {checkpoint.index + 1} · {checkpoint.clock} · {checkpoint.multiple.toFixed(3)}× · Keep running?
          </p>
          <p className="mt-1 text-sm text-amber-50">{checkpoint.message}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void session.decide(checkpoint.index, "continue")}
              disabled={session.pending}
              className="whitespace-nowrap rounded-full bg-cyan-300 px-5 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-200 disabled:opacity-60"
            >
              Keep running
            </button>
            <button
              type="button"
              onClick={() => void session.decide(checkpoint.index, "stop")}
              disabled={session.pending}
              className="whitespace-nowrap rounded-full border border-white/20 px-5 py-2 text-sm text-white hover:border-rose-300/60 disabled:opacity-60"
            >
              Stop for today
            </button>
          </div>
        </div>
      ) : null}

      {live ? (
        <dl className="mt-4 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <div>
            <dt className="text-slate-500">Session</dt>
            <dd className="mt-0.5 text-slate-200">{live.session_date}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Last update</dt>
            <dd className="mt-0.5 text-slate-200">{formatEt(live.last_tick_at)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Next bar</dt>
            <dd className="mt-0.5 text-slate-200">{session.active ? formatEt(live.next_bar_at) : "—"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">P&amp;L</dt>
            <dd className="mt-0.5 text-slate-200">
              {lastEquity !== null ? formatSignedMoney(lastEquity - live.config.starting_balance) : formatMoney(live.config.starting_balance)}
            </dd>
          </div>
          {live.message && live.status !== "awaiting_decision" ? <p className="col-span-full text-slate-400">{live.message}</p> : null}
          <p className="col-span-full text-slate-500">
            {live.notify_channel ? `Notifications go to ${live.notify_channel}.` : "No phone notifications for this session."}
            {live.notify_error ? ` Last notification failed: ${live.notify_error}` : ""}
            {alerts.supported && session.active ? (
              alerts.enabled ? (
                " Browser alerts are on for this tab."
              ) : (
                <>
                  {" "}
                  <button type="button" onClick={() => void alerts.enable()} className="text-cyan-200 underline-offset-2 hover:underline">
                    Alert me in this browser
                  </button>
                </>
              )
            ) : null}
          </p>
        </dl>
      ) : null}

      {!session.active ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
          <label className="grid gap-1 text-xs text-slate-400">
            Phone notifications (optional): an ntfy.sh topic, Discord webhook, or Slack webhook URL
            <input
              value={notifyUrl}
              onChange={(event) => setNotifyUrl(event.target.value)}
              placeholder="https://ntfy.sh/your-private-topic"
              className="w-full rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-300/60"
            />
          </label>
          <button
            type="button"
            onClick={() => void session.start(config, notifyUrl)}
            disabled={!available || session.pending}
            className="whitespace-nowrap rounded-full bg-emerald-300 px-5 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {session.pending ? "Connecting…" : "Start live session"}
          </button>
          <p className="text-[11px] text-slate-500 sm:col-span-2">
            {available
              ? "Uses the rules above. Starts at 09:30 ET if launched early. ntfy is a free phone app: subscribe to the same topic to get the keep-running prompts."
              : "Live mode needs ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY on the API."}
          </p>
        </div>
      ) : null}

      {session.error ? (
        <div className="mt-4">
          <StatePanel title="Live desk" message={session.error} tone="danger" />
        </div>
      ) : null}
    </Card>
  );
}

/** Replaces the replay controls while the console shows the live session. */
export function LiveBar({ live, onReplay }: { live: DeskLiveSession; onReplay: () => void }) {
  const status = STATUS_COPY[live.status];
  const frames = live.result?.frames ?? [];
  const expected = live.result?.session_lengths?.[0] ?? 78;
  const progress = Math.min(frames.length / expected, 1);

  return (
    <div className="mt-3 flex flex-wrap items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-2.5">
      <span className={clsx("flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold", status.tone)}>
        {live.status === "running" ? <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 motion-safe:animate-pulse" /> : null}
        {status.label}
      </span>
      <span className="relative h-1.5 min-w-[8rem] flex-1 rounded-full bg-white/10" aria-label={`${frames.length} of ${expected} bars`}>
        <span className="absolute inset-y-0 left-0 rounded-full bg-emerald-400" style={{ width: `${progress * 100}%` }} />
      </span>
      <span className="font-mono text-xs tabular-nums text-slate-400">
        bar {frames.length}/{expected} · next {formatEt(live.next_bar_at)}
      </span>
      <button type="button" onClick={onReplay} className="text-xs text-slate-400 underline-offset-2 hover:text-white hover:underline">
        Replay today so far
      </button>
    </div>
  );
}
