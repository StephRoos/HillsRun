import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const {
  mockSetAthlete,
  mockGenerateMutate,
  mockRevokeMutate,
  mockRedeemMutate,
  mockRemoveAthleteMutate,
  mockRemoveCoachMutate,
  mockData,
} = vi.hoisted(() => ({
  mockSetAthlete: vi.fn(),
  mockGenerateMutate: vi.fn(),
  mockRevokeMutate: vi.fn(),
  mockRedeemMutate: vi.fn(),
  mockRemoveAthleteMutate: vi.fn(),
  mockRemoveCoachMutate: vi.fn(),
  mockData: {
    statusData: null as any,
    inviteCodesData: null as any,
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual("@tanstack/react-query");
  return {
    ...actual,
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@/lib/coach-context", () => ({
  useCoachContext: () => ({ setAthlete: mockSetAthlete }),
}));

vi.mock("@/lib/garmin-api", () => ({
  setViewAsAthlete: vi.fn(),
}));

vi.mock("@/hooks/use-coaching", () => ({
  useCoachingStatus: () => ({ data: mockData.statusData }),
  useGenerateInviteCode: () => ({ mutate: mockGenerateMutate, isPending: false }),
  useInviteCodes: () => ({ data: mockData.inviteCodesData }),
  useRevokeInviteCode: () => ({ mutate: mockRevokeMutate }),
  useRedeemInviteCode: () => ({ mutate: mockRedeemMutate, isPending: false }),
  useRemoveAthlete: () => ({ mutate: mockRemoveAthleteMutate }),
  useRemoveCoach: () => ({ mutate: mockRemoveCoachMutate }),
}));

import { CoachingSection } from "../coaching-section";

describe("CoachingSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockData.statusData = null;
    mockData.inviteCodesData = null;
  });

  it("renders coaching and my coaches cards", () => {
    render(<CoachingSection />);

    expect(screen.getByText("Coaching")).toBeInTheDocument();
    expect(screen.getByText("My Coaches")).toBeInTheDocument();
  });

  it("renders generate invite code button", () => {
    render(<CoachingSection />);

    expect(screen.getByText("Generate invite code")).toBeInTheDocument();
  });

  it("renders athletes list when present", () => {
    mockData.statusData = {
      athletes: [
        { athlete_user_id: 1, display_name: "Alice", email: "alice@test.com" },
        { athlete_user_id: 2, display_name: null, email: "bob@test.com" },
      ],
      coaches: [],
    };

    render(<CoachingSection />);

    expect(screen.getByText("Your athletes")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("bob@test.com")).toBeInTheDocument();
  });

  it("renders coaches list when present", () => {
    mockData.statusData = {
      athletes: [],
      coaches: [
        { coach_better_auth_id: "c1", coach_name: "Coach Mike", coach_email: "mike@coach.com" },
      ],
    };

    render(<CoachingSection />);

    expect(screen.getByText("Active coaches")).toBeInTheDocument();
    expect(screen.getByText("Coach Mike")).toBeInTheDocument();
  });

  it("renders invite code input", () => {
    render(<CoachingSection />);

    expect(screen.getByPlaceholderText("Enter invite code")).toBeInTheDocument();
    expect(screen.getByText("Link")).toBeInTheDocument();
  });

  it("does not show athletes section when empty", () => {
    mockData.statusData = { athletes: [], coaches: [] };

    render(<CoachingSection />);

    expect(screen.queryByText("Your athletes")).not.toBeInTheDocument();
  });

  it("shows pending invite codes", () => {
    mockData.inviteCodesData = [
      { id: 1, code: "ABC123", status: "pending" },
      { id: 2, code: "XYZ789", status: "redeemed" },
    ];

    render(<CoachingSection />);

    expect(screen.getByText("Pending invite codes")).toBeInTheDocument();
    expect(screen.getByText("ABC123")).toBeInTheDocument();
    expect(screen.queryByText("XYZ789")).not.toBeInTheDocument();
  });

  it("renders view button for each athlete", () => {
    mockData.statusData = {
      athletes: [
        { athlete_user_id: 1, display_name: "Alice", email: "alice@test.com" },
      ],
      coaches: [],
    };

    render(<CoachingSection />);

    expect(screen.getByLabelText("View Alice's data")).toBeInTheDocument();
  });

  it("displays fallback for athlete without name or email", () => {
    mockData.statusData = {
      athletes: [
        { athlete_user_id: 99, display_name: null, email: null },
      ],
      coaches: [],
    };

    render(<CoachingSection />);

    expect(screen.getByText("User #99")).toBeInTheDocument();
  });
});
