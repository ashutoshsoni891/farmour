import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import i18n from "../i18n";
import { LanguageSwitch } from "./LanguageSwitch";

describe("LanguageSwitch", () => {
  it("defaults to Hindi and switches to English", async () => {
    render(<LanguageSwitch />);
    expect(i18n.language).toBe("hi");
    expect(screen.getByRole("button", { name: "हिन्दी" })).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(screen.getByRole("button", { name: "English" }));
    expect(i18n.language).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(localStorage.getItem("farm.lang")).toBe("en");
  });
});
