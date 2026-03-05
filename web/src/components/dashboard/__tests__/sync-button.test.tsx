import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";

const { mockTrigger, mockState } = vi.hoisted(() => ({
  mockTrigger: vi.fn(),
  mockState: { isSyncing: false },
}));

vi.mock("@/hooks/use-sync", () => ({
  useTriggerSync: () => ({ trigger: mockTrigger, isSyncing: mockState.isSyncing }),
}));

import { SyncButton } from "../sync-button";

describe("SyncButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockState.isSyncing = false;
  });

  it("renders Sync text when idle", () => {
    render(<SyncButton />);
    expect(screen.getByText("Sync")).toBeInTheDocument();
    expect(screen.getByRole("button")).not.toBeDisabled();
  });

  it("shows Syncing... and is disabled when syncing", () => {
    mockState.isSyncing = true;
    render(<SyncButton />);

    expect(screen.getByText("Syncing...")).toBeInTheDocument();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("calls trigger on click", () => {
    render(<SyncButton />);

    act(() => {
      screen.getByRole("button").click();
    });

    expect(mockTrigger).toHaveBeenCalled();
  });

  it("has correct aria-label when idle", () => {
    render(<SyncButton />);
    expect(screen.getByLabelText("Sync Garmin data")).toBeInTheDocument();
  });

  it("has correct aria-label when syncing", () => {
    mockState.isSyncing = true;
    render(<SyncButton />);
    expect(screen.getByLabelText("Syncing Garmin data")).toBeInTheDocument();
  });
});
