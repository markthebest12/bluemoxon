import { describe, it, expect } from "vitest";
import { formatBytes, formatCost } from "../format";

describe("formatBytes", () => {
  it("formats bytes correctly", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(1048576)).toBe("1.0 MB");
    expect(formatBytes(1073741824)).toBe("1.00 GB");
    expect(formatBytes(1500000000)).toBe("1.40 GB");
  });

  it("handles zero", () => {
    expect(formatBytes(0)).toBe("0 B");
  });
});

describe("formatCost", () => {
  it("calculates S3 monthly cost", () => {
    expect(formatCost(1073741824)).toBe("~$0.02/month");
    expect(formatCost(10737418240)).toBe("~$0.23/month");
    expect(formatCost(107374182400)).toBe("~$2.30/month");
  });

  it("handles small sizes", () => {
    expect(formatCost(1000000)).toBe("~$0.00/month");
  });
});
