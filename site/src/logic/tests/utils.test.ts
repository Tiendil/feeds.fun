import {afterEach, describe, expect, it, vi} from "vitest";
import DOMPurify from "dompurify";
import {purifyBody, purifyTitle} from "@/logic/utils";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("purifyBody", () => {
  it("sets required security attributes for links", () => {
    const raw = '<a href="https://example.com" target="_self" rel="noopener" referrerpolicy="unsafe-url">Example</a>';

    const purified = purifyBody({raw, default_: "No description"});

    expect(purified).toContain('href="https://example.com"');
    expect(purified).toContain('target="_blank"');
    expect(purified).toContain('rel="noopener noreferrer nofollow"');
    expect(purified).toContain('referrerpolicy="strict-origin-when-cross-origin"');
  });
});

describe("purifyTitle", () => {
  it("returns default value for null and empty values", () => {
    expect(purifyTitle({raw: null, default_: "No title"})).toBe("No title");
    expect(purifyTitle({raw: "   ", default_: "No title"})).toBe("No title");
  });

  it("sets required security attributes for links in sanitized output", () => {
    vi.spyOn(DOMPurify, "sanitize").mockReturnValue(
      '<a href="https://example.com" target="_self" rel="noopener" referrerpolicy="unsafe-url">Example</a>'
    );

    const purified = purifyTitle({raw: "Example title", default_: "No title"});

    expect(purified).toContain('href="https://example.com"');
    expect(purified).toContain('target="_blank"');
    expect(purified).toContain('rel="noopener noreferrer nofollow"');
    expect(purified).toContain('referrerpolicy="strict-origin-when-cross-origin"');
  });
});
