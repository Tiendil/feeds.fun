import {describe, expect, it} from "vitest";
import {sanitizeIframes} from "@/logic/iframeSanitizer";

function iframeFor(src: string) {
  const sanitized = sanitizeIframes(`<iframe src="${src}"></iframe>`);
  const parsed = new DOMParser().parseFromString(sanitized, "text/html");
  return parsed.body.querySelector("iframe");
}

describe("sanitizeIframes", () => {
  it.each([
    "https://www.youtube-nocookie.com/embed/video-id",
    "https://www.youtube-nocookie.com/embed/videoseries?list=playlist-id",
    "https://www.youtube-nocookie.com/embed",
    "https://player.vimeo.com/video/12345",
    "https://geo.dailymotion.com/player/player-id.html?video=video-id",
    "https://geo.dailymotion.com/player.html?video=video-id",
    "https://www.dailymotion.com/embed/video/video-id",
    "https://embed.ted.com/talks/talk-slug",
    "https://www.ted.com/embed/talks/talk-slug",
    "https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/1",
    "https://open.spotify.com/embed/track/track-id",
    "https://bandcamp.com/EmbeddedPlayer/album=1/size=large",
    "https://www.mixcloud.com/widget/iframe/?feed=%2Fshow%2F",
    "https://embed.music.apple.com/us/album/album-name/12345",
    "https://player.twitch.tv/?channel=channel&parent=feeds.fun",
    "https://clips.twitch.tv/embed?clip=clip-id&parent=feeds.fun",
    "https://player.bilibili.com/player.html?bvid=video-id",
    "https://archive.org/embed/archive-id",
    "https://framatube.org/videos/embed/video-id",
    "https://videopress.com/v/video-id",
    "https://www.openstreetmap.org/export/embed.html?bbox=1%2C2%2C3%2C4",
    "https://www.google.com/maps/embed/v1/place?key=key&q=place",
    "https://www.google.com/maps/embed?pb=map-data",
    "https://www.google.com/maps/d/embed?mid=map-id",
    "https://maps.google.com/maps?q=place&output=embed",
    "https://umap.openstreetmap.fr/en/map/map-name_123",
    "https://docs.google.com/presentation/d/e/presentation-id/embed",
    "https://docs.google.com/document/d/e/document-id/pub?embedded=true",
    "https://docs.google.com/spreadsheets/d/e/sheet-id/pubhtml",
    "https://speakerdeck.com/player/deck-id",
    "https://www.scribd.com/embeds/document-id/content",
    "https://www.slideshare.net/slideshow/embed_code/key",
    "https://www.canva.com/design/design-id/view?embed",
    "https://view.officeapps.live.com/op/embed.aspx?src=https%3A%2F%2Fexample.com%2Fdocument.docx"
  ])("allows provider embed URL %s", (src) => {
    expect(iframeFor(src)).not.toBeNull();
  });

  it("rewrites YouTube embeds to the privacy-enhanced host", () => {
    const iframe = iframeFor("https://www.youtube.com/embed/video-id?start=10#fragment");

    expect(iframe?.getAttribute("src")).toBe("https://www.youtube-nocookie.com/embed/video-id?start=10");
  });

  it("adds Vimeo DNT parameter", () => {
    const iframe = iframeFor("https://player.vimeo.com/video/12345?h=hash");

    expect(iframe?.getAttribute("src")).toBe("https://player.vimeo.com/video/12345?h=hash&dnt=1");
  });

  it("removes iframes that do not satisfy source requirements", () => {
    const sanitized = sanitizeIframes(`
      <iframe></iframe>
      <iframe src="http://www.youtube-nocookie.com/embed/video-id"></iframe>
      <iframe src="https://www.youtube-nocookie.com.evil.example/embed/video-id"></iframe>
      <iframe src="https://www.youtube-nocookie.com/watch?v=video-id"></iframe>
      <iframe src="/embed/video-id"></iframe>
    `);

    expect(sanitized).not.toContain("<iframe");
  });

  it("rebuilds allowed iframes with only generated attributes and title", () => {
    const sanitized = sanitizeIframes(`
      <iframe
        src="https://www.youtube-nocookie.com/embed/video-id"
        width="560"
        height="315"
        title="Video title"
        srcdoc="<p>HTML</p>"
        loading="eager"
        referrerpolicy="no-referrer"
        sandbox="allow-top-navigation"
        allow="camera"
        allowfullscreen="false"
        name="source-frame">
      </iframe>
    `);
    const parsed = new DOMParser().parseFromString(sanitized, "text/html");
    const iframe = parsed.body.querySelector("iframe");

    expect(iframe?.getAttribute("src")).toBe("https://www.youtube-nocookie.com/embed/video-id");
    expect(iframe?.getAttribute("title")).toBe("Video title");
    expect(iframe?.getAttribute("loading")).toBe("lazy");
    expect(iframe?.getAttribute("referrerpolicy")).toBe("strict-origin-when-cross-origin");
    expect(iframe?.getAttribute("sandbox")).toBe(
      "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
    );
    expect(iframe?.getAttribute("allow")).toBe("fullscreen; picture-in-picture; encrypted-media");
    expect(iframe?.hasAttribute("allowfullscreen")).toBe(true);
    expect(iframe?.hasAttribute("width")).toBe(false);
    expect(iframe?.hasAttribute("height")).toBe(false);
    expect(iframe?.hasAttribute("srcdoc")).toBe(false);
    expect(iframe?.hasAttribute("name")).toBe(false);
  });

  it("uses a fallback iframe title when source title is missing", () => {
    expect(iframeFor("https://archive.org/embed/archive-id")?.getAttribute("title")).toBe("Embedded media");
  });
});
