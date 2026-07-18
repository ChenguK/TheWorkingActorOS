import { Children, cloneElement, isValidElement, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type ReactElement, type ReactNode } from "react";
import { useState } from "react";
import { ChevronDown, ChevronRight, Loader2, Trash2 } from "lucide-react";
import { statusToneClasses, statusToneFromLabel, type StatusTone } from "../design-system";

export function Section({
  title,
  actions,
  defaultOpen = true,
  children
}: {
  title: string;
  actions?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="min-w-0 max-w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex min-w-0 flex-col gap-3 border-b border-slate-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          className="inline-flex min-w-0 items-center gap-2 text-left text-base font-semibold text-ink"
          onClick={() => setOpen((current) => !current)}
          aria-expanded={open}
        >
          {open ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
          <span className="min-w-0 break-words">{title}</span>
        </button>
        <div className="flex min-w-0 flex-wrap items-center justify-end gap-2">{actions}</div>
      </div>
      {open && <div className="min-w-0 max-w-full overflow-hidden p-4">{children}</div>}
    </section>
  );
}

export function Field({
  label,
  children
}: {
  label: string;
  children: ReactNode;
}) {
  const fallbackName = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  const namedChildren = Children.map(children, (child) => {
    if (!isValidElement(child) || typeof child.type !== "string") {
      return child;
    }
    if (!["input", "select", "textarea"].includes(child.type)) {
      return child;
    }
    const field = child as ReactElement<{ id?: string; name?: string }>;
    return cloneElement(field, {
      id: field.props.id ?? fallbackName,
      name: field.props.name ?? fallbackName
    });
  });
  return (
    <label className="grid min-w-0 gap-1 text-xs font-medium text-slate-700">
      <span className="break-words">{label}</span>
      {namedChildren}
    </label>
  );
}

export const inputClass =
  "min-w-0 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-xs text-ink outline-none transition focus:border-accent focus:ring-2 focus:ring-blue-100";

export function Button({
  children,
  type = "button",
  variant = "primary",
  onClick,
  disabled
}: {
  children: ReactNode;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "danger";
  onClick?: () => void;
  disabled?: boolean;
}) {
  const variants = {
    primary: "bg-accent text-white hover:bg-blue-700",
    secondary: "border border-slate-300 bg-white text-ink hover:bg-slate-50",
    danger: "bg-red-600 text-white hover:bg-red-700"
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex min-w-0 max-w-full items-center justify-center whitespace-normal break-words rounded-md px-3 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]}`}
    >
      {children}
    </button>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="min-w-0 max-w-full overflow-hidden rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center text-xs text-slate-600">
      {children}
    </div>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: StatusTone }) {
  if (tone !== "neutral") {
    return (
      <span className={`inline-flex max-w-full items-center break-words rounded border px-2 py-1 text-xs font-medium ${statusToneClasses[tone]}`}>
        {children}
      </span>
    );
  }
  return (
    <span className="inline-flex max-w-full items-center break-words rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">
      {children}
    </span>
  );
}

export function StatusBadge({ children, tone }: { children: ReactNode; tone?: StatusTone }) {
  return <Badge tone={tone ?? statusToneFromLabel(String(children ?? ""))}>{children}</Badge>;
}

export function DetailDisclosure({
  label,
  children,
  defaultOpen = false
}: {
  label: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="min-w-0 max-w-full overflow-hidden rounded-md border border-slate-200 bg-slate-50">
      <button
        type="button"
        className="flex min-w-0 w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs font-semibold text-ink"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        <span className="min-w-0 break-words">{label}</span>
        {open ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
      </button>
      {open && <div className="min-w-0 max-w-full overflow-hidden break-words border-t border-slate-200 px-3 py-3 text-xs text-slate-700">{children}</div>}
    </div>
  );
}

export function ActionCard({
  title,
  status,
  meta,
  children,
  primaryAction,
  secondaryAction,
  details
}: {
  title: ReactNode;
  status?: ReactNode;
  meta?: ReactNode;
  children?: ReactNode;
  primaryAction?: ReactNode;
  secondaryAction?: ReactNode;
  details?: ReactNode;
}) {
  return (
    <article className="min-w-0 max-w-full overflow-hidden rounded-md border border-slate-200 bg-white p-3 shadow-sm">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="break-words text-sm font-semibold text-ink">{title}</h3>
          {meta && <div className="mt-1 break-words text-xs text-slate-500">{meta}</div>}
        </div>
        {status && <div className="shrink-0">{status}</div>}
      </div>
      {children && <div className="mt-3 min-w-0 max-w-full overflow-hidden break-words text-xs text-slate-700">{children}</div>}
      {(primaryAction || secondaryAction) && (
        <div className="mt-3 flex flex-wrap gap-2">
          {primaryAction}
          {secondaryAction}
        </div>
      )}
      {details && <div className="mt-3 min-w-0 max-w-full overflow-hidden break-words">{details}</div>}
    </article>
  );
}

export function ExpandableCard({
  title,
  summary,
  status,
  actions,
  children,
  defaultOpen = false
}: {
  title: ReactNode;
  summary?: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <article className="min-w-0 max-w-full overflow-hidden rounded-md border border-slate-200 bg-white text-xs shadow-sm">
      <div className="flex min-w-0 items-center gap-3 px-3 py-2">
        <button
          type="button"
          className="inline-flex min-w-0 flex-1 items-center gap-2 text-left"
          onClick={() => setOpen((current) => !current)}
          aria-expanded={open}
        >
          {open ? <ChevronDown className="h-4 w-4 shrink-0 text-slate-500" /> : <ChevronRight className="h-4 w-4 shrink-0 text-slate-500" />}
          <span className="min-w-0">
            <span className="block break-words font-semibold text-ink">{title}</span>
            {summary && <span className="mt-0.5 block break-words text-slate-500">{summary}</span>}
          </span>
        </button>
        {status && <div className="shrink-0">{status}</div>}
        {actions && <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">{actions}</div>}
      </div>
      {open && <div className="min-w-0 max-w-full overflow-hidden border-t border-slate-200 p-3 text-slate-700">{children}</div>}
    </article>
  );
}

export function CompactListRow({
  title,
  subtitle,
  meta,
  actions,
  onClick,
  expanded = false
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  onClick?: () => void;
  expanded?: boolean;
}) {
  return (
    <div className="flex min-w-0 max-w-full items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-sm">
      {onClick && (
        <button type="button" className="shrink-0 text-slate-500" onClick={onClick} aria-label={expanded ? "Collapse row" : "Expand row"} aria-expanded={expanded}>
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
      )}
      <div className="min-w-0 flex-1">
        <div className="break-words font-semibold text-ink">{title}</div>
        {subtitle && <div className="mt-0.5 break-words text-slate-500">{subtitle}</div>}
      </div>
      {meta && <div className="hidden shrink-0 text-slate-500 sm:block">{meta}</div>}
      {actions && <div className="flex shrink-0 flex-wrap justify-end gap-2">{actions}</div>}
    </div>
  );
}

export function LinkedTitle({
  children,
  href,
  external = false,
  className = "",
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & {
  children: ReactNode;
  href: string;
  external?: boolean;
}) {
  return (
    <a
      className={`break-words font-semibold text-ink transition hover:text-accent hover:underline ${className}`}
      href={href}
      target={external ? "_blank" : props.target}
      rel={external ? "noreferrer" : props.rel}
      {...props}
    >
      {children}
    </a>
  );
}

export function AsyncButton({
  loading,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  loading?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex min-w-0 max-w-full items-center justify-center gap-2 whitespace-normal break-words rounded-md px-3 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
        props.className ?? "bg-accent text-white hover:bg-blue-700"
      }`}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

export function ConfirmAction({
  label,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  message,
  onConfirm,
  tone = "danger"
}: {
  label: ReactNode;
  confirmLabel?: ReactNode;
  cancelLabel?: ReactNode;
  message?: ReactNode;
  onConfirm: () => void | Promise<void>;
  tone?: StatusTone;
}) {
  const [confirming, setConfirming] = useState(false);
  if (confirming) {
    return (
      <span className="inline-flex min-w-0 max-w-full flex-wrap items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs">
        {message && <span className="break-words text-slate-600">{message}</span>}
        <button type="button" className={`inline-flex items-center gap-1 font-semibold ${tone === "danger" ? "text-red-700" : "text-accent"}`} onClick={() => void onConfirm()}>
          <Trash2 className="h-3.5 w-3.5" />
          {confirmLabel}
        </button>
        <button type="button" className="font-semibold text-slate-600 hover:underline" onClick={() => setConfirming(false)}>
          {cancelLabel}
        </button>
      </span>
    );
  }
  return (
    <button type="button" className={`text-xs font-semibold hover:underline ${tone === "danger" ? "text-red-700" : "text-accent"}`} onClick={() => setConfirming(true)}>
      {label}
    </button>
  );
}

export function SectionHeader({
  title,
  subtitle,
  actions,
  eyebrow
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{eyebrow}</p>}
        <h2 className="break-words text-base font-semibold text-ink">{title}</h2>
        {subtitle && <p className="mt-1 break-words text-xs text-slate-600">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function LoadingIndicator({ label = "Loading..." }: { label?: ReactNode }) {
  return (
    <div className="inline-flex items-center gap-2 text-xs font-medium text-slate-600" role="status" aria-live="polite">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function CapabilityNotice({
  label,
  children,
  tone = "warning"
}: {
  label?: ReactNode;
  children: ReactNode;
  tone?: StatusTone;
}) {
  return (
    <div className={`min-w-0 max-w-full overflow-hidden rounded-md border p-3 text-xs ${statusToneClasses[tone]}`}>
      {label && <p className="mb-1 font-semibold">{label}</p>}
      <div className="break-words">{children}</div>
    </div>
  );
}

export function FieldGrid({ children, columns = 2 }: { children: ReactNode; columns?: 1 | 2 | 3 | 4 }) {
  const classes = {
    1: "grid gap-3",
    2: "grid gap-3 md:grid-cols-2",
    3: "grid gap-3 md:grid-cols-2 xl:grid-cols-3",
    4: "grid gap-3 md:grid-cols-2 xl:grid-cols-4"
  };
  return <div className={classes[columns]}>{children}</div>;
}

export function InfoBadge({ label, value }: { label?: ReactNode; value: ReactNode }) {
  return (
    <span className="inline-flex max-w-full items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700">
      {label && <span className="font-semibold text-slate-500">{label}</span>}
      <span className="min-w-0 break-words">{value}</span>
    </span>
  );
}

export function CollapsiblePanel({
  title,
  children,
  defaultOpen = false,
  actions
}: {
  title: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  actions?: ReactNode;
}) {
  return (
    <DetailDisclosure label={String(title)} defaultOpen={defaultOpen}>
      {actions && <div className="mb-3 flex flex-wrap gap-2">{actions}</div>}
      {children}
    </DetailDisclosure>
  );
}

export function EntitySummary({
  title,
  subtitle,
  meta,
  status,
  actions
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  meta?: ReactNode;
  status?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <article className="min-w-0 max-w-full overflow-hidden rounded-md border border-slate-200 bg-white p-3 text-xs shadow-sm">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="break-words font-semibold text-ink">{title}</h3>
          {subtitle && <p className="mt-1 break-words text-slate-600">{subtitle}</p>}
          {meta && <div className="mt-2 flex flex-wrap gap-2">{meta}</div>}
        </div>
        {status && <div className="shrink-0">{status}</div>}
      </div>
      {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
    </article>
  );
}
