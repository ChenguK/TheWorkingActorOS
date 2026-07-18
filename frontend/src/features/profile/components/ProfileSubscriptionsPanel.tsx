import { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { CapabilityNotice, EmptyState, Field, Section, StatusBadge, inputClass } from "../../../components/ui";
import { useUpdatePlatformSubscription } from "../hooks/useProfileQueries";
import type { CastingPlatformSubscription } from "../types";

export function ProfileSubscriptionsPanel({
  subscriptions
}: {
  subscriptions: CastingPlatformSubscription[];
}) {
  const updateMutation = useUpdatePlatformSubscription();
  const [savingId, setSavingId] = useState<string | null>(null);

  async function update(subscription: CastingPlatformSubscription, patch: Partial<CastingPlatformSubscription>) {
    setSavingId(subscription.id);
    try {
      await updateMutation.mutateAsync({ id: subscription.id, patch });
    } finally {
      setSavingId(null);
    }
  }

  return (
    <Section title="Casting Platform Subscriptions" actions={<ShieldCheck className="h-5 w-5 text-slate-500" />}>
      <CapabilityNotice tone="info">
        This app does not log into casting platforms or scrape private breakdowns. This section only records the platforms you personally subscribe to and whether they should appear in your manual daily check-in.
      </CapabilityNotice>
      {subscriptions.length === 0 ? (
        <EmptyState>Loading platform subscription defaults...</EmptyState>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {subscriptions.map((subscription) => (
            <article key={subscription.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-ink">{subscription.platform_name}</h3>
                  <p className="text-slate-600">{subscription.has_subscription ? "Subscribed" : "Not subscribed"} · {subscription.active ? "Active" : "Inactive"}</p>
                </div>
                <StatusBadge>{savingId === subscription.id ? "Saving" : subscription.has_subscription ? "Check-In Enabled" : "Off"}</StatusBadge>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    name={`has_subscription_${subscription.id}`}
                    type="checkbox"
                    checked={subscription.has_subscription}
                    onChange={(event) => void update(subscription, { has_subscription: event.target.checked })}
                  />
                  I have this subscription
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    name={`active_subscription_${subscription.id}`}
                    type="checkbox"
                    checked={subscription.active}
                    onChange={(event) => void update(subscription, { active: event.target.checked })}
                  />
                  Include in daily check-in
                </label>
                <Field label="Subscription Level">
                  <input
                    className={inputClass}
                    defaultValue={subscription.subscription_level ?? ""}
                    onBlur={(event) => void update(subscription, { subscription_level: event.target.value || null })}
                    placeholder="Plus, Premium, Basic"
                  />
                </Field>
                <Field label="Renewal Date">
                  <input
                    className={inputClass}
                    type="date"
                    defaultValue={subscription.renewal_date ?? ""}
                    onBlur={(event) => void update(subscription, { renewal_date: event.target.value || null })}
                  />
                </Field>
                <Field label="Monthly Cost">
                  <input
                    className={inputClass}
                    type="number"
                    min={0}
                    step="0.01"
                    defaultValue={subscription.monthly_cost ?? ""}
                    onBlur={(event) => void update(subscription, { monthly_cost: event.target.value ? Number(event.target.value) : null })}
                  />
                </Field>
                <Field label="Annual Cost">
                  <input
                    className={inputClass}
                    type="number"
                    min={0}
                    step="0.01"
                    defaultValue={subscription.annual_cost ?? ""}
                    onBlur={(event) => void update(subscription, { annual_cost: event.target.value ? Number(event.target.value) : null })}
                  />
                </Field>
              </div>
              <div className="mt-3">
                <Field label="Notes">
                  <textarea
                    className={inputClass}
                    defaultValue={subscription.notes ?? ""}
                    onBlur={(event) => void update(subscription, { notes: event.target.value || null })}
                    placeholder="What you usually check here, renewal notes, subscription details"
                  />
                </Field>
              </div>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}
