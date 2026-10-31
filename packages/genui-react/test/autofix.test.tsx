import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GenUIRenderer } from "genui-react";

describe("auto-fixed responses", () => {
  it("render the corrected program, not the broken first attempt", async () => {
    // What genui-py's autofix() streams: attempt 1, a content marker, then the fix.
    const response = 'root = Nope("broken attempt")\n]]>openui:content\nroot = TextContent("corrected program")';
    render(<GenUIRenderer response={response} />);
    await waitFor(() => expect(screen.getByText("corrected program")).toBeTruthy());
    expect(screen.queryByText(/broken attempt/)).toBeNull();
  });

  it("also when the marker arrives mid-line", async () => {
    const response = 'root = TextContent("broken attem]]>openui:content\nroot = TextContent("second try")';
    render(<GenUIRenderer response={response} />);
    await waitFor(() => expect(screen.getByText("second try")).toBeTruthy());
    expect(screen.queryByText(/broken attem/)).toBeNull();
  });
});
