import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../services/api/errors";
import { renderWithRouter, screen, waitFor, within } from "../../../test/testUtils";
import type { ActorProfile, AvailabilityBlock, AuditionCalendarEvent } from "../../../types/domain";
import {
  createAvailabilityBlock,
  createCalendarEvent,
  deleteAvailabilityBlock,
  deleteCalendarEvent,
  listAvailabilityBlocks,
  listCalendarEvents,
  updateAvailabilityBlock,
  updateCalendarEvent
} from "../api";
import { ActorCalendar } from "./ActorCalendar";

vi.mock("@fullcalendar/react", () => ({
  default: ({ events, editable, eventDrop, eventResize }: { events: Array<{ title?: string }>; editable?: boolean; eventDrop?: unknown; eventResize?: unknown }) => <div data-testid="full-calendar" data-editable={String(Boolean(editable))} data-event-drop={String(Boolean(eventDrop))} data-event-resize={String(Boolean(eventResize))}>{events.map((event) => event.title).join(", ")}</div>
}));

vi.mock("../api", () => ({
  createAvailabilityBlock: vi.fn(),
  createCalendarEvent: vi.fn(),
  deleteAvailabilityBlock: vi.fn(),
  deleteCalendarEvent: vi.fn(),
  listAvailabilityBlocks: vi.fn(),
  listCalendarEvents: vi.fn(),
  updateAvailabilityBlock: vi.fn(),
  updateCalendarEvent: vi.fn()
}));

const actor = { id: "actor-1" } as ActorProfile;
const calendarEvent: AuditionCalendarEvent = {
  id: "event-1",
  title: "Callback with Atlas",
  event_type: "Virtual Callback",
  start_datetime: "2026-11-01T01:30:00-04:00",
  end_datetime: "2026-11-01T02:30:00-05:00",
  is_virtual: true,
  created_at: "2026-07-16T12:00:00Z",
  updated_at: "2026-07-16T12:00:00Z"
};
const availability: AvailabilityBlock = {
  id: "availability-1",
  actor_profile_id: "actor-1",
  title: "Booked out",
  block_type: "Already Booked",
  start_date: "2026-07-20T00:00:00-04:00",
  end_date: "2026-07-21T00:00:00-04:00",
  created_at: "2026-07-16T12:00:00Z",
  updated_at: "2026-07-16T12:00:00Z"
};

function renderCalendar() {
  return renderWithRouter(
    <ActorCalendar actor={actor} selfTapes={[]} opportunities={[]} callbackEvents={[]} submissions={[]} commandCenter={null} />
  );
}

describe("ActorCalendar server state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listCalendarEvents).mockResolvedValue([]);
    vi.mocked(listAvailabilityBlocks).mockResolvedValue([]);
  });

  it("shows initial loading and API error states", async () => {
    vi.mocked(listCalendarEvents).mockReturnValueOnce(new Promise(() => undefined));
    const loading = renderCalendar();
    expect(screen.getByRole("status")).toHaveTextContent("Loading Calendar");
    loading.unmount();

    vi.mocked(listCalendarEvents).mockRejectedValueOnce(new ApiError({ message: "Calendar unavailable", status: 503 }));
    renderCalendar();
    expect(await screen.findByRole("alert")).toHaveTextContent("Calendar unavailable");
  });

  it("renders event and availability lists", async () => {
    vi.mocked(listCalendarEvents).mockResolvedValue([calendarEvent]);
    vi.mocked(listAvailabilityBlocks).mockResolvedValue([availability]);
    renderCalendar();
    expect((await screen.findAllByText("Callback with Atlas")).length).toBe(2);
    expect(screen.getByText("Booked out")).toBeInTheDocument();
    expect(screen.getByTestId("full-calendar")).toHaveTextContent("Callback with Atlas");
    expect(screen.getByTestId("full-calendar")).toHaveAttribute("data-editable", "false");
    expect(screen.getByTestId("full-calendar")).toHaveAttribute("data-event-drop", "false");
    expect(screen.getByTestId("full-calendar")).toHaveAttribute("data-event-resize", "false");
    expect(screen.getByText(/Calendar editing is form-based/)).toBeInTheDocument();
  });

  it("creates an event without invoking a workflow refresh", async () => {
    vi.mocked(createCalendarEvent).mockResolvedValue(calendarEvent);
    const { user } = renderCalendar();
    await user.type(await screen.findByLabelText("Event Title"), "Callback with Atlas");
    await user.type(screen.getByLabelText("Starts"), "2026-07-20T10:30");
    await user.click(screen.getByRole("button", { name: "Create Calendar Event" }));
    await waitFor(() => expect(createCalendarEvent).toHaveBeenCalledWith(expect.objectContaining({ start_datetime: "2026-07-20T10:30" })));
    expect(listCalendarEvents).toHaveBeenCalledTimes(2);
    expect(listAvailabilityBlocks).toHaveBeenCalledTimes(1);
  });

  it("shows a safe mutation failure and preserves the event draft", async () => {
    vi.mocked(createCalendarEvent).mockRejectedValue(new ApiError({ message: "Event could not be saved", status: 422 }));
    const { user } = renderCalendar();
    const title = await screen.findByLabelText("Event Title");
    await user.type(title, "Keep this draft");
    await user.type(screen.getByLabelText("Starts"), "2026-07-20T10:30");
    await user.click(screen.getByRole("button", { name: "Create Calendar Event" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Event could not be saved");
    expect(title).toHaveValue("Keep this draft");
  });

  it("updates an event title and deletes an event", async () => {
    vi.mocked(listCalendarEvents).mockResolvedValue([calendarEvent]);
    vi.mocked(updateCalendarEvent).mockResolvedValue({ ...calendarEvent, title: "Renamed callback" });
    vi.mocked(deleteCalendarEvent).mockResolvedValue(undefined);
    const { user } = renderCalendar();
    const item = (await screen.findAllByText("Callback with Atlas")).find((node) => node.closest("article"))?.closest("article");
    expect(item).not.toBeNull();
    await user.click(within(item!).getByRole("button", { name: "Edit Calendar Event" }));
    const titleInput = within(item!).getByLabelText("Event Title");
    await user.clear(titleInput);
    await user.type(titleInput, "Renamed callback");
    await user.click(within(item!).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(updateCalendarEvent).toHaveBeenCalledWith("event-1", { title: "Renamed callback" }));
    await user.click(within(item!).getByRole("button", { name: "Delete Calendar Event" }));
    await waitFor(() => expect(deleteCalendarEvent).toHaveBeenCalledWith("event-1"));
  });

  it("keeps linked workflow Calendar rows read-only", async () => {
    vi.mocked(listCalendarEvents).mockResolvedValue([{ ...calendarEvent, opportunity_id: "opportunity-1" }]);
    renderCalendar();
    const item = (await screen.findAllByText("Callback with Atlas")).find((node) => node.closest("article"))?.closest("article");
    expect(item).not.toBeNull();
    expect(within(item!).getByText(/Read-only linked workflow event/)).toHaveTextContent("Breakdowns");
    expect(within(item!).queryByRole("button", { name: /Edit Calendar Event/ })).not.toBeInTheDocument();
    expect(within(item!).queryByRole("button", { name: /Delete Calendar Event/ })).not.toBeInTheDocument();
  });

  it("creates, updates, and deletes availability with focused invalidation", async () => {
    vi.mocked(listAvailabilityBlocks).mockResolvedValue([availability]);
    vi.mocked(createAvailabilityBlock).mockResolvedValue(availability);
    vi.mocked(updateAvailabilityBlock).mockResolvedValue({ ...availability, title: "Vacation" });
    vi.mocked(deleteAvailabilityBlock).mockResolvedValue(undefined);
    const { user } = renderCalendar();
    await screen.findByText("Booked out");
    await user.type(screen.getByLabelText("Title"), "Training");
    await user.type(screen.getByLabelText("Start"), "2026-07-20T09:00");
    await user.type(screen.getByLabelText("End"), "2026-07-20T12:00");
    await user.click(screen.getByRole("button", { name: "Add Availability Block" }));
    await waitFor(() => expect(createAvailabilityBlock).toHaveBeenCalled());

    const saved = screen.getByText("Booked out").parentElement!;
    await user.click(within(saved).getByRole("button", { name: "Edit" }));
    const title = within(saved).getByLabelText("Availability Title");
    await user.clear(title);
    await user.type(title, "Vacation");
    await user.click(within(saved).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(updateAvailabilityBlock).toHaveBeenCalledWith("availability-1", { title: "Vacation" }));
    await user.click(within(saved).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(deleteAvailabilityBlock).toHaveBeenCalledWith("availability-1"));
    expect(listCalendarEvents).toHaveBeenCalledTimes(1);
  });
});
