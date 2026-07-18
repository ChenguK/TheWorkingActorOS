import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createAuditionCalendarEvent, createAuditionNote, createSelfTapeTask, updateSelfTapeTask } from "../api";
import { useQueryClient } from "@tanstack/react-query";
import { calendarEventListKey } from "../../calendar";
import { auditionKeys, useCreateSubmission, useDeleteSubmission, useUpdateSubmissionStatus, useUpdateWorkflowSelfTape } from "./useAuditionQueries";
import type { ActorProfile, Opportunity, SelfTapeTaskEditFormState, SelfTapeWorkflow, Submission, SubmissionFormState, SubmissionStatus } from "../types";
import { auditionNotes, parseAuditionText, preparationText, stringValue, toDateTimeLocal } from "../utils";

const initialForm: SubmissionFormState = {
  opportunity_id: "",
  asset_ids: [],
  current_status: "Submitted",
  notes: "",
  audition_text: "",
  tape_due_at: "",
  audition_date: "",
  audition_location: "",
  virtual_audition_link: "",
  self_tape_submission_link: "",
  preparation_instructions: "",
  submission_instructions: "",
  create_calendar: true,
  create_journal: true,
  create_self_tape: true,
  submission_fee: "",
  media_fee: "",
  travel_cost: "",
  housing_cost: "",
  parking_cost: "",
  other_cost: ""
};

export function useSubmissionTracker({
  actor,
  opportunities,
  submissions,
  selfTapes
}: {
  actor: ActorProfile | null;
  opportunities: Opportunity[];
  submissions: Submission[];
  selfTapes: SelfTapeWorkflow[];
}) {
  const queryClient = useQueryClient();
  const createSubmission = useCreateSubmission();
  const updateTape = useUpdateWorkflowSelfTape();
  const updateStatus = useUpdateSubmissionStatus();
  const deleteSubmissionMutation = useDeleteSubmission();
  const [formOpen, setFormOpen] = useState(submissions.length === 0);
  const [urlPrefillHandled, setUrlPrefillHandled] = useState(false);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [editingTapeId, setEditingTapeId] = useState<string | null>(null);
  const [tapeEditForm, setTapeEditForm] = useState<SelfTapeTaskEditFormState>({
    status: "Not Started",
    tape_due_at: "",
    upload_link: "",
    slate_requirements: "",
    wardrobe_notes: "",
    reader_needed: false
  });
  const [form, setForm] = useState<SubmissionFormState>(initialForm);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!actor) return;
    const selected = opportunities.find((opportunity) => opportunity.id === form.opportunity_id);
    const notes = auditionNotes(form, selected);
    const submission = await createSubmission.mutateAsync({
      actor_profile_id: actor.id,
      opportunity_id: form.opportunity_id,
      asset_ids: form.asset_ids,
      current_status: form.current_status,
      notes,
      submission_fee: Number(form.submission_fee || 0),
      media_fee: Number(form.media_fee || 0),
      travel_cost: Number(form.travel_cost || 0),
      housing_cost: Number(form.housing_cost || 0),
      parking_cost: Number(form.parking_cost || 0),
      other_cost: Number(form.other_cost || 0)
    });
    await createAuditionLinkedRecords(form, submission, selected);
    setForm(initialForm);
    setSubmissionMessage(`Submission added for ${selected?.role ?? "this role"} on ${new Date().toLocaleDateString()}.`);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: auditionKeys.selfTapes }),
      queryClient.invalidateQueries({ queryKey: auditionKeys.performanceNotes }),
      queryClient.invalidateQueries({ queryKey: calendarEventListKey })
    ]);
  }

  const selectBreakdown = useCallback((opportunityId: string) => {
    const opportunity = opportunities.find((item) => item.id === opportunityId);
    if (!opportunity) {
      setForm({ ...form, opportunity_id: opportunityId });
      return;
    }
    const source = opportunity.source_metadata ?? {};
    const role = opportunity.role_details ?? {};
    const production = opportunity.production_details ?? {};
    const tapeDue = stringValue(role.tape_due_date) || stringValue(role.self_tape_due_date) || opportunity.audition_deadline || opportunity.submission_deadline || "";
    const auditionDate = opportunity.audition_deadline || stringValue(role.audition_date) || "";
    setForm({
      ...form,
      opportunity_id: opportunityId,
      current_status: opportunity.audition_type === "Self-Tape" ? "Requested" : form.current_status,
      tape_due_at: toDateTimeLocal(tapeDue),
      audition_date: toDateTimeLocal(auditionDate),
      audition_location: opportunity.audition_location || stringValue(role.audition_location_name) || stringValue(production.audition_location_name) || "",
      virtual_audition_link: stringValue(source.virtual_audition_link) || stringValue(role.virtual_audition_link) || "",
      self_tape_submission_link: stringValue(source.self_tape_submission_link) || stringValue(role.self_tape_submission_link) || stringValue(source.submission_link) || "",
      preparation_instructions: preparationText(opportunity),
      submission_instructions: stringValue(role.submission_instructions) || stringValue(source.submission_instructions) || "",
      notes: auditionNotes(form, opportunity)
    });
  }, [form, opportunities]);

  useEffect(() => {
    if (urlPrefillHandled) return;
    const breakdownId = new URLSearchParams(window.location.search).get("breakdownId");
    if (!breakdownId || !opportunities.some((opportunity) => opportunity.id === breakdownId)) return;
    setFormOpen(true);
    selectBreakdown(breakdownId);
    setUrlPrefillHandled(true);
  }, [opportunities, selectBreakdown, urlPrefillHandled]);

  function parseAuditionDetails() {
    const parsed = parseAuditionText(form.audition_text);
    setForm({
      ...form,
      ...parsed,
      notes: [form.notes, parsed.notes].filter(Boolean).join("\n\n")
    });
  }

  async function createAuditionLinkedRecords(current: SubmissionFormState, submission: Submission, opportunity?: Opportunity) {
    const title = opportunity ? `${opportunity.role} · ${opportunity.project}` : "Audition";
    if (current.create_self_tape && current.tape_due_at && opportunity) {
      const existingTape = selfTapes.find((workflow) => workflow.opportunity_id === opportunity.id && !workflow.submission_id);
      const payload = {
        opportunity_id: opportunity.id,
        submission_id: submission.id,
        status: existingTape?.status ?? "Not Started",
        tape_due_at: current.tape_due_at,
        upload_link: current.self_tape_submission_link || null,
        slate_requirements: current.preparation_instructions || null,
        wardrobe_notes: existingTape?.wardrobe_notes ?? null
      };
      if (existingTape) await updateSelfTapeTask(existingTape.id, payload);
      else await createSelfTapeTask(payload);
    }
    if (current.create_calendar) {
      const dateValue = current.tape_due_at || current.audition_date;
      if (dateValue) {
        await createAuditionCalendarEvent({
          title,
          event_type: current.tape_due_at ? "Self-Tape Due" : current.virtual_audition_link ? "Virtual Callback" : "In-Person Callback",
          opportunity_id: opportunity?.id ?? null,
          submission_id: submission.id,
          start_datetime: dateValue,
          location: current.audition_location || null,
          is_virtual: Boolean(current.virtual_audition_link),
          notes: current.preparation_instructions || current.submission_instructions || null
        });
      }
    }
    if (current.create_journal) {
      await createAuditionNote({
        submission_id: submission.id,
        opportunity_id: opportunity?.id ?? null,
        date: new Date().toISOString().slice(0, 10),
        preparation_notes: current.preparation_instructions || null,
        casting_notes: current.submission_instructions || null,
        follow_up_notes: current.self_tape_submission_link || current.virtual_audition_link || null
      });
    }
  }

  function toggleAsset(assetId: string) {
    setForm((current) => ({
      ...current,
      asset_ids: current.asset_ids.includes(assetId)
        ? current.asset_ids.filter((id) => id !== assetId)
        : [...current.asset_ids, assetId]
    }));
  }

  function startTapeEdit(workflow: SelfTapeWorkflow) {
    setEditingTapeId(workflow.id);
    setTapeEditForm({
      status: workflow.status,
      tape_due_at: toDateTimeLocal(workflow.tape_due_at),
      upload_link: workflow.upload_link ?? "",
      slate_requirements: workflow.slate_requirements ?? "",
      wardrobe_notes: workflow.wardrobe_notes ?? "",
      reader_needed: workflow.reader_needed
    });
  }

  async function saveTapeEdit(workflow: SelfTapeWorkflow) {
    await updateTape.mutateAsync({ id: workflow.id, patch: {
      status: tapeEditForm.status,
      tape_due_at: tapeEditForm.tape_due_at || null,
      upload_link: tapeEditForm.upload_link || null,
      slate_requirements: tapeEditForm.slate_requirements || null,
      wardrobe_notes: tapeEditForm.wardrobe_notes || null,
      reader_needed: tapeEditForm.reader_needed
    }});
    setEditingTapeId(null);
  }

  async function quickUpdateTapeStatus(workflowId: string, status: string) {
    await updateTape.mutateAsync({ id: workflowId, patch: { status } });
  }

  async function markSubmissionStatus(submissionId: string, status: SubmissionStatus) {
    await updateStatus.mutateAsync({ id: submissionId, status });
  }

  async function removeSubmission(submissionId: string) {
    await deleteSubmissionMutation.mutateAsync(submissionId);
  }

  return {
    formOpen,
    setFormOpen,
    submissionMessage,
    editingTapeId,
    setEditingTapeId,
    tapeEditForm,
    setTapeEditForm,
    form,
    setForm,
    submit,
    selectBreakdown,
    parseAuditionDetails,
    toggleAsset,
    startTapeEdit,
    saveTapeEdit,
    quickUpdateTapeStatus,
    markSubmissionStatus,
    removeSubmission
  };
}
