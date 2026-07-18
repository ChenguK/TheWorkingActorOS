import { CareerIntelligencePanel } from "@/features/career-intelligence";
import { useSubmissions } from "@/features/auditions";
import { useSystemCapabilities } from "@/services/system";

export function CareerPage() {
  const submissions = useSubmissions();
  const capabilities = useSystemCapabilities();
  return <CareerIntelligencePanel data={{ capabilities: capabilities.data ?? null, submissions: submissions.data ?? [] }} />;
}
