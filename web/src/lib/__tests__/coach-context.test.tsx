import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { CoachProvider, useCoachContext } from "../coach-context";

function wrapper({ children }: { children: React.ReactNode }) {
  return <CoachProvider>{children}</CoachProvider>;
}

describe("CoachProvider", () => {
  it("provides default values", () => {
    const { result } = renderHook(() => useCoachContext(), { wrapper });

    expect(result.current.athleteUserId).toBeNull();
    expect(result.current.athleteName).toBeNull();
    expect(result.current.isViewingAthlete).toBe(false);
  });

  it("setAthlete updates userId and name atomically", () => {
    const { result } = renderHook(() => useCoachContext(), { wrapper });

    act(() => {
      result.current.setAthlete(42, "Alice");
    });

    expect(result.current.athleteUserId).toBe(42);
    expect(result.current.athleteName).toBe("Alice");
    expect(result.current.isViewingAthlete).toBe(true);
  });

  it("clearing athlete resets to default", () => {
    const { result } = renderHook(() => useCoachContext(), { wrapper });

    act(() => {
      result.current.setAthlete(42, "Alice");
    });
    expect(result.current.isViewingAthlete).toBe(true);

    act(() => {
      result.current.setAthlete(null, null);
    });

    expect(result.current.athleteUserId).toBeNull();
    expect(result.current.athleteName).toBeNull();
    expect(result.current.isViewingAthlete).toBe(false);
  });

  it("switching athlete updates both fields", () => {
    const { result } = renderHook(() => useCoachContext(), { wrapper });

    act(() => {
      result.current.setAthlete(1, "Alice");
    });
    expect(result.current.athleteUserId).toBe(1);

    act(() => {
      result.current.setAthlete(2, "Bob");
    });
    expect(result.current.athleteUserId).toBe(2);
    expect(result.current.athleteName).toBe("Bob");
  });

  it("context is accessible from nested components", () => {
    function Display() {
      const { athleteName, isViewingAthlete } = useCoachContext();
      return (
        <div>
          <span data-testid="name">{athleteName ?? "none"}</span>
          <span data-testid="viewing">{String(isViewingAthlete)}</span>
        </div>
      );
    }

    function Setter() {
      const { setAthlete } = useCoachContext();
      return (
        <button onClick={() => setAthlete(5, "Charlie")}>set</button>
      );
    }

    render(
      <CoachProvider>
        <Display />
        <Setter />
      </CoachProvider>
    );

    expect(screen.getByTestId("name")).toHaveTextContent("none");
    expect(screen.getByTestId("viewing")).toHaveTextContent("false");

    act(() => {
      screen.getByText("set").click();
    });

    expect(screen.getByTestId("name")).toHaveTextContent("Charlie");
    expect(screen.getByTestId("viewing")).toHaveTextContent("true");
  });

  it("useCoachContext outside provider returns defaults", () => {
    const { result } = renderHook(() => useCoachContext());

    expect(result.current.athleteUserId).toBeNull();
    expect(result.current.athleteName).toBeNull();
    expect(result.current.isViewingAthlete).toBe(false);
  });
});
