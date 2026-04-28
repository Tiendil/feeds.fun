type PathMatcher = (url: URL) => boolean;

type ProviderRule = {
  hostname: string;
  matchesPath: PathMatcher;
  rewriteUrl?: (url: URL) => URL;
};

export const DOM_PURIFY_IFRAME_OPTIONS = {
  ADD_TAGS: ["iframe"],
  ADD_ATTR: ["src", "title"]
};

const GENERATED_IFRAME_ATTRIBUTES = {
  loading: "lazy",
  referrerpolicy: "strict-origin-when-cross-origin",
  sandbox: "allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox",
  allow: "fullscreen; picture-in-picture; encrypted-media"
} as const;

const IFRAME_TITLE_DEFAULT = "Embedded media";

const oneSegmentAfter = (prefix: string): PathMatcher => {
  const expression = new RegExp(`^${prefix}/[^/]+$`);

  return (url: URL) => expression.test(url.pathname);
};

const startsWithPath = (prefix: string): PathMatcher => {
  const expression = new RegExp(`^${prefix}/.+$`);

  return (url: URL) => expression.test(url.pathname);
};

function rewriteYoutubeToPrivacyEnhanced(url: URL) {
  const rewritten = new URL(url.toString());
  rewritten.hostname = "www.youtube-nocookie.com";
  return rewritten;
}

function addVimeoDnt(url: URL) {
  const rewritten = new URL(url.toString());
  rewritten.searchParams.set("dnt", "1");
  return rewritten;
}

function hasQueryParameter(url: URL, name: string, value?: string) {
  if (!url.searchParams.has(name)) {
    return false;
  }

  return value === undefined || url.searchParams.get(name) === value;
}

function isAbsoluteHttpsUrl(rawUrl: string) {
  if (rawUrl.trim() !== rawUrl) {
    return false;
  }

  try {
    const url = new URL(rawUrl);
    return url.protocol === "https:";
  } catch {
    return false;
  }
}

function sanitizedUrl(rawUrl: string) {
  if (!isAbsoluteHttpsUrl(rawUrl)) {
    return null;
  }

  const url = new URL(rawUrl);
  const rule = PROVIDER_RULES.find((candidate) => candidate.hostname === url.hostname);

  if (rule === undefined || !rule.matchesPath(url)) {
    return null;
  }

  url.username = "";
  url.password = "";
  url.hash = "";

  const rewritten = rule.rewriteUrl?.(url) ?? url;

  return rewritten.toString();
}

const PROVIDER_RULES: ProviderRule[] = [
  {
    hostname: "www.youtube-nocookie.com",
    matchesPath: (url) => /^\/embed(\/[^/]+)?$/.test(url.pathname)
  },
  {
    hostname: "www.youtube.com",
    matchesPath: (url) => /^\/embed(\/[^/]+)?$/.test(url.pathname),
    rewriteUrl: rewriteYoutubeToPrivacyEnhanced
  },
  {
    hostname: "player.vimeo.com",
    matchesPath: (url) => /^\/video\/\d+$/.test(url.pathname),
    rewriteUrl: addVimeoDnt
  },
  {
    hostname: "geo.dailymotion.com",
    matchesPath: (url) => /^\/player(\/[^/]+\.html|\.html)$/.test(url.pathname)
  },
  {
    hostname: "www.dailymotion.com",
    matchesPath: (url) => /^\/embed\/video\/[^/]+$/.test(url.pathname)
  },
  {
    hostname: "embed.ted.com",
    matchesPath: oneSegmentAfter("/talks")
  },
  {
    hostname: "www.ted.com",
    matchesPath: startsWithPath("/embed")
  },
  {
    hostname: "w.soundcloud.com",
    matchesPath: (url) => url.pathname === "/player/"
  },
  {
    hostname: "open.spotify.com",
    matchesPath: (url) => /^\/embed\/[^/]+\/[^/]+$/.test(url.pathname)
  },
  {
    hostname: "bandcamp.com",
    matchesPath: startsWithPath("/EmbeddedPlayer")
  },
  {
    hostname: "www.mixcloud.com",
    matchesPath: (url) => url.pathname === "/widget/iframe/"
  },
  {
    hostname: "embed.music.apple.com",
    matchesPath: (url) => /^\/[a-z]{2}\/[^/]+\/.+$/.test(url.pathname)
  },
  {
    hostname: "player.twitch.tv",
    matchesPath: (url) => url.pathname === "/"
  },
  {
    hostname: "clips.twitch.tv",
    matchesPath: (url) => url.pathname === "/embed"
  },
  {
    hostname: "player.bilibili.com",
    matchesPath: (url) => url.pathname === "/player.html"
  },
  {
    hostname: "archive.org",
    matchesPath: oneSegmentAfter("/embed")
  },
  {
    hostname: "framatube.org",
    matchesPath: oneSegmentAfter("/videos/embed")
  },
  {
    hostname: "videopress.com",
    matchesPath: oneSegmentAfter("/v")
  },
  {
    hostname: "www.openstreetmap.org",
    matchesPath: (url) => url.pathname === "/export/embed.html"
  },
  {
    hostname: "www.google.com",
    matchesPath: (url) =>
      /^\/maps\/embed\/v1\/[^/]+$/.test(url.pathname) ||
      url.pathname === "/maps/embed" ||
      url.pathname === "/maps/d/embed"
  },
  {
    hostname: "maps.google.com",
    matchesPath: (url) => url.pathname === "/maps" && hasQueryParameter(url, "output", "embed")
  },
  {
    hostname: "umap.openstreetmap.fr",
    matchesPath: (url) => /^\/([a-z]{2}\/)?map\/[^/]+_\d+$/.test(url.pathname)
  },
  {
    hostname: "docs.google.com",
    matchesPath: (url) =>
      /^\/presentation\/d\/e\/[^/]+\/embed$/.test(url.pathname) ||
      (/^\/document\/d\/e\/[^/]+\/pub$/.test(url.pathname) && hasQueryParameter(url, "embedded", "true")) ||
      /^\/spreadsheets\/d\/e\/[^/]+\/pubhtml$/.test(url.pathname)
  },
  {
    hostname: "speakerdeck.com",
    matchesPath: oneSegmentAfter("/player")
  },
  {
    hostname: "www.scribd.com",
    matchesPath: (url) => /^\/embeds\/[^/]+\/content$/.test(url.pathname)
  },
  {
    hostname: "www.slideshare.net",
    matchesPath: startsWithPath("/slideshow/embed_code")
  },
  {
    hostname: "www.canva.com",
    matchesPath: (url) => /^\/design\/[^/]+\/view$/.test(url.pathname) && hasQueryParameter(url, "embed")
  },
  {
    hostname: "view.officeapps.live.com",
    matchesPath: (url) => {
      const source = url.searchParams.get("src");

      return (
        url.pathname === "/op/embed.aspx" &&
        source !== null &&
        isAbsoluteHttpsUrl(source) &&
        Array.from(url.searchParams.keys()).every((key) => key === "src")
      );
    }
  }
];

function setGeneratedAttributes(iframe: HTMLIFrameElement, src: string, title: string | null) {
  iframe.setAttribute("src", src);
  iframe.setAttribute("title", title || IFRAME_TITLE_DEFAULT);
  iframe.setAttribute("loading", GENERATED_IFRAME_ATTRIBUTES.loading);
  iframe.setAttribute("referrerpolicy", GENERATED_IFRAME_ATTRIBUTES.referrerpolicy);
  iframe.setAttribute("sandbox", GENERATED_IFRAME_ATTRIBUTES.sandbox);
  iframe.setAttribute("allow", GENERATED_IFRAME_ATTRIBUTES.allow);
  iframe.setAttribute("allowfullscreen", "");
}

function replacementForIframe(source: HTMLIFrameElement) {
  const src = source.getAttribute("src");

  if (src === null) {
    return null;
  }

  const sanitizedSrc = sanitizedUrl(src);

  if (sanitizedSrc === null) {
    return null;
  }

  const iframe = source.ownerDocument.createElement("iframe");

  setGeneratedAttributes(iframe, sanitizedSrc, source.getAttribute("title"));

  return iframe;
}

export function sanitizeIframes(html: string) {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  const iframes = parsed.body.querySelectorAll("iframe");

  for (const iframe of iframes) {
    const replacement = replacementForIframe(iframe);

    if (replacement === null) {
      iframe.remove();
      continue;
    }

    iframe.replaceWith(replacement);
  }

  return parsed.body.innerHTML;
}
