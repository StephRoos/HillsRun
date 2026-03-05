import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";

const { mockConnectMutate, mockMfaMutate, mockHookState } = vi.hoisted(() => ({
  mockConnectMutate: vi.fn(),
  mockMfaMutate: vi.fn(),
  mockHookState: {
    connectPending: false,
    mfaPending: false,
  },
}));

vi.mock("@/hooks/use-garmin-account", () => ({
  useConnectGarmin: () => ({
    isPending: mockHookState.connectPending,
    mutate: mockConnectMutate,
  }),
  useSubmitMfa: () => ({
    isPending: mockHookState.mfaPending,
    mutate: mockMfaMutate,
  }),
}));

import { GarminConnectForm } from "../garmin-connect-form";

describe("GarminConnectForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHookState.connectPending = false;
    mockHookState.mfaPending = false;
  });

  it("renders credentials form initially", () => {
    render(<GarminConnectForm />);

    expect(screen.getByLabelText("Garmin email")).toBeInTheDocument();
    expect(screen.getByLabelText("Garmin password")).toBeInTheDocument();
    expect(screen.getByText("Connect Garmin")).toBeInTheDocument();
  });

  it("submit button is disabled when fields are empty", () => {
    render(<GarminConnectForm />);

    // Button text is "Connect Garmin" — get the actual button
    const button = screen.getByRole("button", { name: /Connect Garmin/i });
    expect(button).toBeDisabled();
  });

  it("calls connect mutation on submit with filled fields", async () => {
    render(<GarminConnectForm />);

    fireEvent.change(screen.getByLabelText("Garmin email"), {
      target: { value: "test@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Garmin password"), {
      target: { value: "password123" },
    });

    fireEvent.submit(screen.getByText("Connect Garmin").closest("form")!);

    expect(mockConnectMutate).toHaveBeenCalledWith(
      { email: "test@test.com", password: "password123" },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
  });

  it("shows Connecting... when pending", () => {
    mockHookState.connectPending = true;

    render(<GarminConnectForm />);

    expect(screen.getByText("Connecting...")).toBeInTheDocument();
  });

  it("switches to MFA form after MFA response", () => {
    mockConnectMutate.mockImplementation((_creds: any, opts: any) => {
      opts.onSuccess({ needs_mfa: true, mfa_session_id: "sess-123" });
    });

    render(<GarminConnectForm />);

    fireEvent.change(screen.getByLabelText("Garmin email"), {
      target: { value: "test@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Garmin password"), {
      target: { value: "password123" },
    });

    fireEvent.submit(screen.getByText("Connect Garmin").closest("form")!);

    // Now we should see MFA form
    expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
    expect(screen.getByText("Verify")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("disables inputs when pending", () => {
    mockHookState.connectPending = true;

    render(<GarminConnectForm />);

    expect(screen.getByLabelText("Garmin email")).toBeDisabled();
    expect(screen.getByLabelText("Garmin password")).toBeDisabled();
  });

  it("cancel button returns to credentials form", () => {
    mockConnectMutate.mockImplementation((_creds: any, opts: any) => {
      opts.onSuccess({ needs_mfa: true, mfa_session_id: "sess-123" });
    });

    render(<GarminConnectForm />);

    // Fill and submit to trigger MFA
    fireEvent.change(screen.getByLabelText("Garmin email"), {
      target: { value: "test@test.com" },
    });
    fireEvent.change(screen.getByLabelText("Garmin password"), {
      target: { value: "pass" },
    });
    fireEvent.submit(screen.getByText("Connect Garmin").closest("form")!);

    // Click Cancel
    fireEvent.click(screen.getByText("Cancel"));

    // Should be back to credentials form
    expect(screen.getByLabelText("Garmin email")).toBeInTheDocument();
    expect(screen.getByText("Connect Garmin")).toBeInTheDocument();
  });
});
