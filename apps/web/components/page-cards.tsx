import { Card } from "@tradenoc/ui";
import { StatePanel } from "@/components/state-panels";

export function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card>
      <p className="text-sm uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <p className="mt-4 text-3xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-slate-300">{detail}</p>
    </Card>
  );
}

export function ListCard({
  title,
  items,
  emptyMessage,
  emptyActionLabel,
  emptyActionHref,
}: {
  title: string;
  items: string[];
  emptyMessage?: string;
  emptyActionLabel?: string;
  emptyActionHref?: string;
}) {
  return (
    <Card>
      <h2 className="text-lg font-medium text-white">{title}</h2>
      {items.length === 0 ? (
        <div className="mt-4">
          <StatePanel
            title={`No ${title.toLowerCase()} yet`}
            message={emptyMessage ?? "Nothing is available in this section yet."}
            actionLabel={emptyActionLabel}
            actionHref={emptyActionHref}
          />
        </div>
      ) : (
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          {items.map((item) => (
            <li key={item} className="rounded-2xl border border-white/5 bg-white/[0.03] px-4 py-3">
              {item}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
