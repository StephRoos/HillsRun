import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";

const { mockSetAthlete, mockCtx, mockSetViewAsAthlete } = vi.hoisted(() => ({
  mockSetAthlete: vi.fn(),
  mockCtx: {
    isViewingAthlete: false,
    athleteName: null as string | null,
    athleteUserId: null as number | null,
  },
  mockSetViewAsAthlete: vi.fn(),
}));

vi.mock("@/lib/coach-context", () => ({
  useCoachContext: () => ({
    ...mockCtx,
    setAthlete: mockSetAthlete,
  }),
}));

vi.mock("@/lib/garmin-api", () => ({
  setViewAsAthlete: (...args: unknown[]) => mockSetViewAsAthlete(...args),
}));

import { CoachBanner } from "../coach-banner";

describe("CoachBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCtx.isViewingAthlete = false;
    mockCtx.athleteName = null;
    mockCtx.athleteUserId = null;
  });

  it("renders nothing when not viewing athlete", () => {
    const { container } = render(<CoachBanner />);
    expect(container.firstChild).toBeNull();
  });

  it("shows athlete name when viewing athlete", () => {
    mockCtx.isViewingAthlete = true;
    mockCtx.athleteName = "Alice";
    mockCtx.athleteUserId = 42;

    render(<CoachBanner />);

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Back to my data")).toBeInTheDocument();
  });

  it("clears athlete on back button click", () => {
    mockCtx.isViewingAthlete = true;
    mockCtx.athleteName = "Alice";
    mockCtx.athleteUserId = 42;

    render(<CoachBanner />);

    act(() => {
      screen.getByText("Back to my data").click();
    });

    expect(mockSetAthlete).toHaveBeenCalledWith(null, null);
    expect(mockSetViewAsAthlete).toHaveBeenCalledWith(null);
  });
});
