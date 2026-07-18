import { useEffect, useRef, useState, type FormEvent } from "react";
import { errorMessage } from "../../../services/api/errors";
import { splitList } from "../../../utils/tags";
import type { ActorProfile, Asset, AssetType, MaterialFormState } from "../types";
import {
  useAnalyzeMaterial,
  useDeleteMaterial,
  useMaterials,
  useUpdateMaterial,
  useUploadMaterial
} from "./useMaterials";

const initialMaterialForm: MaterialFormState = {
  asset_name: "",
  asset_type: "Headshot" as AssetType,
  description: "",
  tags: "",
  archetype_names: ""
};

export function useMaterialLibrary({
  actor
}: {
  actor: ActorProfile | null;
}) {
  const materialsQuery = useMaterials();
  const uploadMutation = useUploadMaterial();
  const updateMutation = useUpdateMaterial();
  const deleteMutation = useDeleteMaterial();
  const analyzeMutation = useAnalyzeMaterial();
  const emptyStateInitialized = useRef(false);
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<MaterialFormState>(initialMaterialForm);
  const assets = materialsQuery.data ?? [];

  useEffect(() => {
    if (materialsQuery.isSuccess && !emptyStateInitialized.current) {
      emptyStateInitialized.current = true;
      if (assets.length === 0) setFormOpen(true);
    }
  }, [assets.length, materialsQuery.isSuccess]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    setValidationError(null);
    if (!actor) {
      setValidationError("Create an actor profile before uploading materials.");
      return;
    }
    if (!file) {
      setValidationError("Choose a file before uploading this material.");
      return;
    }
    const data = new FormData();
    data.set("actor_profile_id", actor.id);
    data.set("asset_name", form.asset_name);
    data.set("asset_type", form.asset_type);
    data.set("description", form.description);
    data.set("tags", form.tags);
    data.set("archetype_names", form.archetype_names);
    data.set("file", file);
    try {
      const saved = await uploadMutation.mutateAsync(data);
      setForm(initialMaterialForm);
      setFile(null);
      setFileInputKey((current) => current + 1);
      setMessage(`${saved.asset_name} was uploaded to Materials.`);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  async function analyze(assetId: string) {
    try {
      await analyzeMutation.mutateAsync(assetId);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  async function saveEdit(assetId: string, payload: {
    asset_name: string;
    asset_type: AssetType;
    description: string | null;
    tags: string[];
    archetype_names: string[];
    freshness_status: Asset["freshness_status"];
  }) {
    await updateMutation.mutateAsync({ assetId, patch: payload });
  }

  async function remove(assetId: string) {
    try {
      await deleteMutation.mutateAsync(assetId);
    } catch {
      // The mutation retains the standardized ApiError for presentation.
    }
  }

  function selectFile(nextFile: File | null) {
    setFile(nextFile);
    setMessage(null);
    setValidationError(null);
  }

  const mutationError = uploadMutation.error ?? updateMutation.error ?? deleteMutation.error ?? analyzeMutation.error;

  return {
    assets,
    isLoading: materialsQuery.isLoading,
    isRefetching: materialsQuery.isRefetching,
    queryError: materialsQuery.error && !materialsQuery.data ? errorMessage(materialsQuery.error, "Could not load Materials.") : null,
    file,
    fileInputKey,
    saving: uploadMutation.isPending,
    editPending: updateMutation.isPending,
    deletePending: deleteMutation.isPending,
    analyzePending: analyzeMutation.isPending,
    message,
    error: validationError ?? (mutationError ? errorMessage(mutationError, "Could not save this material.") : null),
    formOpen,
    form,
    setForm,
    setFormOpen,
    submit,
    analyze,
    saveEdit,
    remove,
    selectFile
  };
}
