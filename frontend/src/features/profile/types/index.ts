import type {
  ActingCredit,
  ActingCreditCategory,
  ActorProfile,
  Asset,
  PlatformAssetMapping,
  PlatformImportMethod,
  PlatformName,
  PlatformProfile,
  ProfessionalEquipmentProfile,
  PublicProfileImport,
  Representation,
  CastingPlatformSubscription,
  TravelPreference
} from "../../../types/domain";

export type {
  ActingCredit,
  ActingCreditCategory,
  ActorProfile,
  Asset,
  PlatformAssetMapping,
  PlatformImportMethod,
  PlatformName,
  PlatformProfile,
  ProfessionalEquipmentProfile,
  PublicProfileImport,
  Representation,
  CastingPlatformSubscription,
  TravelPreference
};

export type ProfileSetupStep = {
  title: string;
  description: string;
  complete: boolean;
};
