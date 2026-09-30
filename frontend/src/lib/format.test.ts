import { formatDayMonth, formatNumber, formatRupees } from "./format";

describe("Indian formats", () => {
  it("groups digits the Indian way in both languages", () => {
    expect(formatNumber(100000, "en")).toBe("1,00,000");
    expect(formatNumber(12345678, "hi")).toBe("1,23,45,678");
  });

  it("shows paise as rounded rupees", () => {
    expect(formatRupees(4_200_000, "en")).toBe("₹42,000");
    expect(formatRupees(12_345, "hi")).toBe("₹123");
  });

  it("formats dates as 28 Sep / 28 सितंबर in IST", () => {
    const d = new Date("2026-09-27T20:00:00Z"); // 28 Sep 01:30 IST
    expect(formatDayMonth(d, "en")).toBe("28 Sept");
    expect(formatDayMonth(d, "hi")).toBe("28 सितंबर");
  });
});
