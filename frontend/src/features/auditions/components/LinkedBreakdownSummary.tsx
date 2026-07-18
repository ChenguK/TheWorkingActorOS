import type { Opportunity } from "../types";
import { externalBreakdownUrl } from "../utils";

export function OpportunityLink({
  opportunity,
  className = "font-semibold"
}: {
  opportunity: Opportunity;
  className?: string;
}) {
  const label = `${opportunity.role} · ${opportunity.project}`;
  const sourceUrl = externalBreakdownUrl(opportunity);
  if (!sourceUrl) return <span className={`${className} break-words`}>{label}</span>;
  return (
    <a className={`${className} break-words text-accent hover:underline`} href={sourceUrl} target="_blank" rel="noreferrer">
      {label}
    </a>
  );
}
