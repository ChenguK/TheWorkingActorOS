import { Badge } from "../../../components/ui";

export function DataSufficiencyNotice({ state, message }: { state: string; message: string }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{state}</Badge>
        <span className="font-semibold">Track more submissions to unlock this insight.</span>
      </div>
      <p className="mt-2">{message}</p>
      <p className="mt-1 text-amber-900">Next step: keep linking submissions, materials, archetypes, outcomes, and casting offices as you work.</p>
    </div>
  );
}

