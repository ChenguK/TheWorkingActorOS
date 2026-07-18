import { Link } from "react-router-dom";
import { ActionCard, Badge, EmptyState, Section } from "../../../components/ui";
import { useMaterialOptions } from "../../materials";
import { useActingCredits, useActorProfile, usePlatformProfiles, usePublicProfileImports, useRepresentations, useTravelPreferences } from "../hooks/useProfileQueries";
import type { ProfileSetupStep } from "../types";

export function ProfileSetupPanel() {
  const actor = useActorProfile();
  const representations = useRepresentations();
  const travel = useTravelPreferences(actor.data?.id);
  const credits = useActingCredits();
  const materials = useMaterialOptions();
  const platformProfiles = usePlatformProfiles();
  const publicImports = usePublicProfileImports();
  const steps: ProfileSetupStep[] = [
    { title: "Basic Info", description: "Name, SAG status, union status, and current location.", complete: Boolean(actor.data?.name && actor.data.current_location) },
    { title: "Representation", description: "Agency, agent, market, and contact details.", complete: Boolean(representations.data?.length) },
    { title: "Playable Age", description: "Primary and secondary playable age ranges.", complete: Boolean(actor.data?.playable_age_min && actor.data.playable_age_max) },
    { title: "Travel Rules", description: "Audition travel, local hire range, working travel, and housing rules.", complete: Boolean(travel.data) },
    { title: "Credits", description: "Structured TV, film, theater, training, and skills credits.", complete: Boolean(credits.data?.length) },
    { title: "Skills", description: "Special skills and actor-specific strengths.", complete: Boolean(actor.data?.skills?.length) },
    { title: "Materials", description: "Headshots, reels, slates, resumes, and self-tapes.", complete: Boolean(materials.data?.length) },
    { title: "Platform Imports", description: "Draft imports from public links, pasted text, PDFs, screenshots, or CSVs.", complete: Boolean(platformProfiles.data?.length || publicImports.data?.length) }
  ];
  const completeCount = steps.filter((step) => step.complete).length;
  const loading = [actor, representations, travel, credits, materials, platformProfiles, publicImports].some((query) => query.isLoading);

  return <div className="grid gap-4">
    <Section title="Profile Setup" actions={<Link className="text-sm font-semibold text-accent" to="/profile">Edit Profile</Link>}>
      <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center"><div><p className="text-sm text-slate-600">Work through these steps when you have time. The app stays usable while your profile is still in progress.</p><p className="mt-2 text-sm font-semibold text-ink">{loading ? "Loading setup progress…" : `${completeCount} of ${steps.length} steps complete`}</p></div><Link to="/profile" className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50">Open Profile</Link></div>
    </Section>
    <div className="grid gap-3 lg:grid-cols-2">{steps.map((step, index) => <ActionCard key={step.title} title={`${index + 1}. ${step.title}`} status={<Badge>{step.complete ? "Complete" : "Needs Info"}</Badge>} primaryAction={<Link className="text-sm font-semibold text-accent" to="/profile">Edit</Link>}>{step.description}</ActionCard>)}</div>
    {completeCount === steps.length ? <EmptyState>Your setup checklist is complete. You can still update anything from the Profile page.</EmptyState> : <EmptyState>Finish only the parts that matter today. Missing setup items will not block auditions, materials, or breakdowns.</EmptyState>}
  </div>;
}
