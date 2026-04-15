const YOUTUBE_HOSTS = new Set(["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"]);

export function youtubeVideoIdFromUrl(rawUrl: string): string | null {
  const url = new URL(rawUrl);

  if (!YOUTUBE_HOSTS.has(url.hostname)) {
    return null;
  }

  if (url.hostname === "youtu.be") {
    const videoId = url.pathname.split("/").filter(Boolean)[0];

    return videoId ?? null;
  }

  if (url.pathname === "/watch") {
    return url.searchParams.get("v");
  }

  const segments = url.pathname.split("/").filter(Boolean);

  if (segments.length < 2) {
    return null;
  }

  if (!["embed", "shorts", "live"].includes(segments[0])) {
    return null;
  }

  return segments[1];
}
