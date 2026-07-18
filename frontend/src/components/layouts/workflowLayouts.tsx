import type { ReactNode } from "react";

export function WorkflowLayout({ children }: { children: ReactNode }) {
  return <div className="grid min-w-0 max-w-full gap-4">{children}</div>;
}

export function DashboardLayout({ children }: { children: ReactNode }) {
  return <div className="grid min-w-0 max-w-full gap-4 xl:grid-cols-4">{children}</div>;
}

export function SettingsLayout({ children }: { children: ReactNode }) {
  return <div className="grid min-w-0 max-w-full gap-4 lg:grid-cols-[minmax(0,1fr)]">{children}</div>;
}
