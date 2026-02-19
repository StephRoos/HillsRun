import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/hooks/use-online-status", () => ({
  useOnlineStatus: vi.fn(),
}));

import { useOnlineStatus } from "@/hooks/use-online-status";
import { OfflineIndicator } from "../offline-indicator";

const mockUseOnlineStatus = vi.mocked(useOnlineStatus);

describe("OfflineIndicator", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when online", () => {
    mockUseOnlineStatus.mockReturnValue({ isOnline: true });
    const { container } = render(<OfflineIndicator />);
    expect(container.firstChild).toBeNull();
  });

  it("renders offline badge when offline", () => {
    mockUseOnlineStatus.mockReturnValue({ isOnline: false });
    render(<OfflineIndicator />);
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });
});
