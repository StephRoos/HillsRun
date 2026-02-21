import { describe, it, expect } from "vitest";
import {
  formatDuration,
  formatDistance,
  formatPace,
  formatElevation,
  getActivityColor,
  activityTypeLabel,
} from "../lib/utils";

describe("formatDuration", () => {
  it("returns — for null/0", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(0)).toBe("—");
  });

  it("formats seconds only", () => {
    expect(formatDuration(45)).toBe("0m45s");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(125)).toBe("2m05s");
  });

  it("formats hours and minutes", () => {
    expect(formatDuration(3661)).toBe("1h01");
  });

  it("formats large durations", () => {
    expect(formatDuration(7200)).toBe("2h00");
  });
});

describe("formatDistance", () => {
  it("returns — for null/0", () => {
    expect(formatDistance(null)).toBe("—");
    expect(formatDistance(0)).toBe("—");
  });

  it("converts meters to km with 1 decimal", () => {
    expect(formatDistance(10000)).toBe("10.0 km");
    expect(formatDistance(5432)).toBe("5.4 km");
  });
});

describe("formatPace", () => {
  it("returns — for null/0/negative", () => {
    expect(formatPace(null)).toBe("—");
    expect(formatPace(0)).toBe("—");
    expect(formatPace(-1)).toBe("—");
  });

  it("converts speed m/s to pace min/km", () => {
    // 3.0 m/s = 1000/3 = 333.3s/km = 5:33/km
    expect(formatPace(3.0)).toBe("5:33 /km");
  });
});

describe("formatElevation", () => {
  it("returns — for null", () => {
    expect(formatElevation(null)).toBe("—");
  });

  it("rounds to nearest meter", () => {
    expect(formatElevation(123.7)).toBe("124 m");
    expect(formatElevation(0)).toBe("0 m");
  });
});

describe("getActivityColor", () => {
  it("returns blue for running", () => {
    expect(getActivityColor("running")).toBe("#3B82F6");
  });

  it("returns orange for trail_running", () => {
    expect(getActivityColor("trail_running")).toBe("#FF6B00");
  });

  it("returns default grey for unknown type", () => {
    expect(getActivityColor("unknown")).toBe("#94A3B8");
  });

  it("returns default grey for null", () => {
    expect(getActivityColor(null)).toBe("#94A3B8");
  });
});

describe("activityTypeLabel", () => {
  it("returns 'Activity' for null", () => {
    expect(activityTypeLabel(null)).toBe("Activity");
  });

  it("returns mapped label for known types", () => {
    expect(activityTypeLabel("running")).toBe("Running");
    expect(activityTypeLabel("trail_running")).toBe("Trail");
    expect(activityTypeLabel("strength_training")).toBe("Strength");
  });

  it("formats unknown types by replacing underscores", () => {
    expect(activityTypeLabel("open_water_swimming")).toBe("open water swimming");
  });
});
