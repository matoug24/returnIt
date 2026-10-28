import { describe, expect, it } from "vitest";
import { messages } from "./i18n";

describe("translations", () => {
  it("keeps English and French keys in parity", () => {
    expect(Object.keys(messages("en")).sort()).toEqual(Object.keys(messages("fr")).sort());
  });
  it("describes ETA as an estimate", () => {
    expect(messages("en").estimate.toLowerCase()).toContain("estimated");
    expect(messages("fr").estimate.toLowerCase()).toContain("estimée");
  });
});

