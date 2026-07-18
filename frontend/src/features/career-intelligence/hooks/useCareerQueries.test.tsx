import { describe, expect, it, vi } from "vitest";
import { createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { careerKeys, selectCareerTaskOptions, useCareerTasks, useCompleteCareerTask } from "./useCareerQueries";
import { completeCareerTask, listCareerTasks } from "../api";

vi.mock("../api", () => ({
  listCareerTasks: vi.fn(async () => []), getCareerSwot: vi.fn(async () => null), listCastingOffices: vi.fn(async () => []),
  listQuarterlyReviews: vi.fn(async () => []), listDreamReadiness: vi.fn(async () => []), listCastingGoals: vi.fn(async () => []),
  listWatchLists: vi.fn(async () => []), getCareerMemory: vi.fn(async () => null), completeCareerTask: vi.fn(async () => ({})),
  createCareerTask: vi.fn(), updateCareerTask: vi.fn(), deleteCareerTask: vi.fn(), createCastingOffice: vi.fn(), createWatchList: vi.fn(),
  updateWatchList: vi.fn(), deleteWatchList: vi.fn(), generateQuarterlyReview: vi.fn(), createCastingGoal: vi.fn(),
  updateCastingGoal: vi.fn(), deleteCastingGoal: vi.fn(), generateCareerSwot: vi.fn(), updateCareerMemory: vi.fn()
}));

describe("Career queries", () => {
  it("uses the Career API and deterministic task key", async () => {
    const { result } = renderHook(() => useCareerTasks(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(listCareerTasks).toHaveBeenCalledOnce();
    expect(careerKeys.tasks).toEqual(["career", "list", { resource: "tasks" }]);
  });

  it("exposes compact Journal task options without a duplicate query shape", () => {
    expect(selectCareerTaskOptions([{ id: "1", title: "Scene", status: "Not Started" } as never])).toEqual([{ id: "1", title: "Scene", status: "Not Started" }]);
  });

  it("completes a task through the feature API", async () => {
    const { result } = renderHook(() => useCompleteCareerTask(), { wrapper: createTestQueryWrapper() });
    await result.current.mutateAsync("task-1");
    expect(vi.mocked(completeCareerTask).mock.calls[0]?.[0]).toBe("task-1");
  });
});
