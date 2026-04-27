import {afterEach, describe, expect, it, vi} from "vitest";
import DOMPurify from "dompurify";
import {purifyBody, purifyTitle} from "@/logic/utils";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("purifyBody", () => {
  it("removes styling and page behavior attributes", () => {
    const raw = `
      <p aria-label="Summary" class="lead" data-id="42" dir="rtl" id="entry"
         lang="en" onclick="alert()" slot="main" style="color: red" title="Title">Body</p>
      <a href="https://example.com" class="link" download ping="https://tracker.example"
         rel="nofollow" target="_self" type="text/html">Link</a>
      <img alt="Chart" height="100" src="https://example.com/chart.png"
           sizes="(max-width: 600px) 100vw, 600px"
           srcset="https://example.com/chart-2x.png 2x" style="width: 100px"
           width="100" />
      <video controls poster="https://example.com/poster.png" style="width: 100%">
        <source media="(min-width: 800px)" src="https://example.com/video.mp4"
                type="video/mp4" />
        <track default kind="captions" label="English"
               src="https://example.com/captions.vtt" srclang="en" />
      </video>
      <table><tr><th colspan="2" scope="col" style="color:red">Head</th></tr></table>
      <ol reversed start="5" type="A"><li value="7">Item</li></ol>
      <time datetime="2026-04-27">Today</time>
      <svg viewBox="0 0 10 10">
        <path d="M0 0h10v10H0z" fill="red" stroke="blue"></path>
      </svg>
    `;

    const purified = purifyBody({raw, default_: "No description"});

    expect(purified).toContain('aria-label="Summary"');
    expect(purified).toContain('dir="rtl"');
    expect(purified).toContain('href="https://example.com"');
    expect(purified).toContain('lang="en"');
    expect(purified).toContain('src="https://example.com/chart.png"');
    expect(purified).toContain('sizes="(max-width: 600px) 100vw, 600px"');
    expect(purified).toContain('srcset="https://example.com/chart-2x.png 2x"');
    expect(purified).toContain('alt="Chart"');
    expect(purified).toContain('title="Title"');
    expect(purified).toContain("controls");
    expect(purified).toContain('poster="https://example.com/poster.png"');
    expect(purified).toContain('media="(min-width: 800px)"');
    expect(purified).toContain('src="https://example.com/video.mp4"');
    expect(purified).toContain('type="video/mp4"');
    expect(purified).toContain('slot="main"');
    expect(purified).toContain("default");
    expect(purified).toContain('kind="captions"');
    expect(purified).toContain('label="English"');
    expect(purified).toContain('src="https://example.com/captions.vtt"');
    expect(purified).toContain('srclang="en"');
    expect(purified).toContain('colspan="2"');
    expect(purified).toContain('datetime="2026-04-27"');
    expect(purified).toContain("download");
    expect(purified).toContain('scope="col"');
    expect(purified).toContain("reversed");
    expect(purified).toContain('start="5"');
    expect(purified).toContain('type="A"');
    expect(purified).toContain('viewBox="0 0 10 10"');
    expect(purified).toContain('d="M0 0h10v10H0z"');
    expect(purified).toContain('fill="red"');
    expect(purified).toContain('stroke="blue"');
    expect(purified).toContain('value="7"');

    expect(purified).not.toContain('class="');
    expect(purified).not.toContain('data-id="');
    expect(purified).not.toContain('id="');
    expect(purified).not.toContain('onclick="');
    expect(purified).not.toContain('ping="');
    expect(purified).not.toContain('style="');
  });

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
