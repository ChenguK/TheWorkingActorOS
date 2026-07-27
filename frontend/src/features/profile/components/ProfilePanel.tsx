import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import { errorMessage } from "../../../services/api/errors";
import { useMaterialOptions } from "../../materials";
import { useSystemCapabilities } from "../../../services/system";
import { useActingCredits, useActorProfile, useEquipmentProfile, usePlatformAssetMappings, usePlatformProfiles, usePlatformSubscriptions, usePublicProfileImports, useRepresentations, useTravelPreferences } from "../hooks/useProfileQueries";
import { ActingResumeBuilder } from "./ActingResumeBuilder";
import { ActorProfilePanel } from "./ActorProfilePanel";
import { PlatformProfileImportAssistant } from "./PlatformProfileImportAssistant";
import { ProfessionalCapabilitiesPanel } from "./ProfessionalCapabilitiesPanel";
import { ProfileSubscriptionsPanel } from "./ProfileSubscriptionsPanel";
import { TravelPreferencePanel } from "./TravelPreferencePanel";

export function ProfilePanel() {
  const actor = useActorProfile();
  const representations = useRepresentations();
  const travel = useTravelPreferences(actor.data?.id);
  const credits = useActingCredits();
  const subscriptions = usePlatformSubscriptions();
  const equipment = useEquipmentProfile();
  const profiles = usePlatformProfiles();
  const publicImports = usePublicProfileImports();
  const mappings = usePlatformAssetMappings();
  const materials = useMaterialOptions();
  const capabilities = useSystemCapabilities();
  const queries = [actor, representations, travel, credits, subscriptions, equipment, profiles, publicImports, mappings, materials];
  const initialError = queries.find((query) => query.error && !query.data)?.error;

  return (
    <div className="grid gap-4">
      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="text-lg font-bold text-ink">Profile</h2><p className="mt-1 text-sm text-slate-600">Keep your actor profile, travel rules, credits, materials, and platform imports organized here.</p></div>
          <Link to="/profile/setup" className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50">Open Setup Checklist</Link>
        </div>
        {queries.some((query) => query.isLoading) && <p className="mt-3 text-sm text-slate-600">Loading Profile sections…</p>}
        {queries.some((query) => query.isRefetching && !query.isLoading) && <p className="mt-3 text-xs text-slate-500">Refreshing saved Profile data…</p>}
        {initialError && <p className="mt-3 rounded bg-red-50 p-2 text-sm text-red-800">{errorMessage(initialError, "Could not load part of your Profile.")}</p>}
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <ProfileSectionState label="actor profile" loading={actor.isLoading || representations.isLoading} error={actor.error ?? representations.error}><ActorProfilePanel actor={actor.data ?? null} representations={representations.data ?? []} /></ProfileSectionState>
        <ProfileSectionState label="travel preferences" loading={actor.isLoading || travel.isLoading} error={travel.error}><TravelPreferencePanel actor={actor.data ?? null} travel={travel.data ?? null} /></ProfileSectionState>
      </div>
      <ProfileSectionState label="platform subscriptions" loading={subscriptions.isLoading} error={subscriptions.error}><ProfileSubscriptionsPanel subscriptions={subscriptions.data ?? []} /></ProfileSectionState>
      <ProfileSectionState label="professional capabilities" loading={equipment.isLoading} error={equipment.error}><ProfessionalCapabilitiesPanel actor={actor.data ?? null} equipmentProfile={equipment.data ?? null} /></ProfileSectionState>
      <ProfileSectionState label="acting credits" loading={credits.isLoading} error={credits.error}><ActingResumeBuilder actor={actor.data ?? null} credits={credits.data ?? []} /></ProfileSectionState>
      <ProfileSectionState label="platform imports" loading={[profiles, publicImports, mappings, materials].some((query) => query.isLoading)} error={profiles.error ?? publicImports.error ?? mappings.error ?? materials.error}><PlatformProfileImportAssistant actor={actor.data ?? null} assets={materials.data ?? []} profiles={profiles.data ?? []} publicImports={publicImports.data ?? []} mappings={mappings.data ?? []} capabilities={capabilities.data ?? null} /></ProfileSectionState>
    </div>
  );
}

function ProfileSectionState({ label, loading, error, children }: { label: string; loading: boolean; error: unknown; children: ReactNode }) {
  if (loading) return <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">Loading {label}…</section>;
  if (error) return <section className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{errorMessage(error, `Could not load ${label}.`)}</section>;
  return children;
}
