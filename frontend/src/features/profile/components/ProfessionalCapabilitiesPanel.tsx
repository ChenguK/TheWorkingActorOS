import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Briefcase, Clapperboard, Download, Edit3, Eye, EyeOff, MapPin, Save, Star, Trash2, UserRound, X } from "lucide-react";
import { Badge, Button, CapabilityNotice, EmptyState, Field, Section, StatusBadge, inputClass } from "../../../components/ui";
import { formatDateTime } from "../../../utils/dateTime";
import { joinList, splitList } from "../../../utils/tags";
import type {
  ActingCredit,
  ActingCreditCategory,
  ActorProfile,
  Asset,
  AssetType,
  CastingPlatformSubscription,
  PlatformAssetMapping,
  PlatformImportMethod,
  PlatformName,
  PlatformProfile,
  ProfessionalEquipmentProfile,
  PublicProfileImport,
  Representation,
  TravelPreference
} from "../../../types/domain";
import { useUpdateEquipmentProfile } from "../hooks/useProfileQueries";

export function ProfessionalCapabilitiesPanel({
  actor,
  equipmentProfile
}: {
  actor: ActorProfile | null;
  equipmentProfile: ProfessionalEquipmentProfile | null;
}) {
  const updateMutation = useUpdateEquipmentProfile();
  const [equipmentForm, setEquipmentForm] = useState({
    cameras: joinList(equipmentProfile?.cameras ?? []),
    lighting: joinList(equipmentProfile?.lighting ?? []),
    audio_equipment: joinList(equipmentProfile?.audio_equipment ?? []),
    backdrops: joinList(equipmentProfile?.backdrops ?? []),
    editing_software: joinList(equipmentProfile?.editing_software ?? []),
    teleprompter: equipmentProfile?.teleprompter ?? false,
    reader_availability: equipmentProfile?.reader_availability ?? "",
    internet_upload_speed: equipmentProfile?.internet_upload_speed ?? "",
    home_audition_space: equipmentProfile?.home_audition_space ?? "",
    notes: equipmentProfile?.notes ?? ""
  });

  useEffect(() => {
    setEquipmentForm({
      cameras: joinList(equipmentProfile?.cameras ?? []),
      lighting: joinList(equipmentProfile?.lighting ?? []),
      audio_equipment: joinList(equipmentProfile?.audio_equipment ?? []),
      backdrops: joinList(equipmentProfile?.backdrops ?? []),
      editing_software: joinList(equipmentProfile?.editing_software ?? []),
      teleprompter: equipmentProfile?.teleprompter ?? false,
      reader_availability: equipmentProfile?.reader_availability ?? "",
      internet_upload_speed: equipmentProfile?.internet_upload_speed ?? "",
      home_audition_space: equipmentProfile?.home_audition_space ?? "",
      notes: equipmentProfile?.notes ?? ""
    });
  }, [equipmentProfile]);

  async function saveEquipment(event: FormEvent) {
    event.preventDefault();
    await updateMutation.mutateAsync({
      actor_profile_id: actor?.id ?? null,
      cameras: splitList(equipmentForm.cameras),
      lighting: splitList(equipmentForm.lighting),
      audio_equipment: splitList(equipmentForm.audio_equipment),
      backdrops: splitList(equipmentForm.backdrops),
      editing_software: splitList(equipmentForm.editing_software),
      teleprompter: equipmentForm.teleprompter,
      reader_availability: equipmentForm.reader_availability || null,
      internet_upload_speed: equipmentForm.internet_upload_speed || null,
      home_audition_space: equipmentForm.home_audition_space || null,
      notes: equipmentForm.notes || null
    });
  }

  return (
    <Section title="Professional Materials & Equipment Profile">
        <form className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={saveEquipment}>
          <h3 className="font-semibold">Professional Materials & Equipment Profile</h3>
          <Field label="Cameras"><input className={inputClass} value={equipmentForm.cameras} onChange={(e) => setEquipmentForm({ ...equipmentForm, cameras: e.target.value })} /></Field>
          <Field label="Lighting"><input className={inputClass} value={equipmentForm.lighting} onChange={(e) => setEquipmentForm({ ...equipmentForm, lighting: e.target.value })} /></Field>
          <Field label="Audio Equipment"><input className={inputClass} value={equipmentForm.audio_equipment} onChange={(e) => setEquipmentForm({ ...equipmentForm, audio_equipment: e.target.value })} /></Field>
          <Field label="Backdrops"><input className={inputClass} value={equipmentForm.backdrops} onChange={(e) => setEquipmentForm({ ...equipmentForm, backdrops: e.target.value })} /></Field>
          <Field label="Editing Software"><input className={inputClass} value={equipmentForm.editing_software} onChange={(e) => setEquipmentForm({ ...equipmentForm, editing_software: e.target.value })} /></Field>
          <label className="flex items-center gap-2 text-sm"><input name="teleprompter" type="checkbox" checked={equipmentForm.teleprompter} onChange={(e) => setEquipmentForm({ ...equipmentForm, teleprompter: e.target.checked })} />Teleprompter available</label>
          <Field label="Reader Availability"><input className={inputClass} value={equipmentForm.reader_availability} onChange={(e) => setEquipmentForm({ ...equipmentForm, reader_availability: e.target.value })} /></Field>
          <Field label="Internet Upload Speed"><input className={inputClass} value={equipmentForm.internet_upload_speed} onChange={(e) => setEquipmentForm({ ...equipmentForm, internet_upload_speed: e.target.value })} /></Field>
          <Field label="Home Audition Space"><textarea className={inputClass} value={equipmentForm.home_audition_space} onChange={(e) => setEquipmentForm({ ...equipmentForm, home_audition_space: e.target.value })} /></Field>
          <Field label="Notes"><textarea className={inputClass} value={equipmentForm.notes} onChange={(e) => setEquipmentForm({ ...equipmentForm, notes: e.target.value })} /></Field>
          <Button type="submit">Save Capabilities</Button>
        </form>
    </Section>
  );
}
