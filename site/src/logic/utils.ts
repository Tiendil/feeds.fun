import _ from "lodash";
import type * as t from "@/logic/types";
import DOMPurify from "dompurify";

const REQUIRED_LINK_ATTRIBUTES = {
  target: "_blank",
  rel: "noopener noreferrer nofollow",
  referrerpolicy: "strict-origin-when-cross-origin"
} as const;

const SAFE_GLOBAL_BODY_ATTRIBUTES = new Set(["dir", "lang", "title"]);

const SAFE_GLOBAL_BODY_ATTRIBUTE_PREFIXES = ["aria-"];

const FUNCTIONAL_BODY_ATTRIBUTES_BY_TAG = new Map([
  ["a", new Set(["href"])],
  ["area", new Set(["alt", "coords", "href", "shape", "title"])],
  ["audio", new Set(["controls", "src", "title"])],
  ["col", new Set(["span"])],
  ["colgroup", new Set(["span"])],
  ["img", new Set(["alt", "sizes", "src", "srcset", "title"])],
  ["li", new Set(["value"])],
  ["ol", new Set(["reversed", "start"])],
  ["source", new Set(["media", "sizes", "src", "srcset", "type"])],
  ["td", new Set(["colspan", "rowspan"])],
  ["th", new Set(["colspan", "rowspan", "scope"])],
  ["track", new Set(["default", "kind", "label", "src", "srclang"])],
  ["video", new Set(["controls", "poster", "src", "title"])]
]);

function isAllowedBodyAttribute(element: Element, attributeName: string) {
  if (SAFE_GLOBAL_BODY_ATTRIBUTES.has(attributeName)) {
    return true;
  }

  if (SAFE_GLOBAL_BODY_ATTRIBUTE_PREFIXES.some((prefix) => attributeName.startsWith(prefix))) {
    return true;
  }

  return FUNCTIONAL_BODY_ATTRIBUTES_BY_TAG.get(element.tagName.toLowerCase())?.has(attributeName) ?? false;
}

function removeNonFunctionalAttributes(html: string) {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  const elements = parsed.body.querySelectorAll("*");

  for (const element of elements) {
    for (const attribute of Array.from(element.attributes)) {
      if (!isAllowedBodyAttribute(element, attribute.name)) {
        element.removeAttribute(attribute.name);
      }
    }
  }

  return parsed.body.innerHTML;
}

function hardenLinksSecurityAttributes(html: string) {
  const parsed = new DOMParser().parseFromString(html, "text/html");
  const links = parsed.body.querySelectorAll("[href]");

  for (const link of links) {
    link.setAttribute("target", REQUIRED_LINK_ATTRIBUTES.target);
    link.setAttribute("rel", REQUIRED_LINK_ATTRIBUTES.rel);
    link.setAttribute("referrerpolicy", REQUIRED_LINK_ATTRIBUTES.referrerpolicy);
  }

  return parsed.body.innerHTML;
}

export function timeSince(date: Date) {
  const now = new Date();

  const secondsPast = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (secondsPast < 60) {
    return "<min";
  }

  const minutesPast = Math.floor(secondsPast / 60);

  if (minutesPast < 60) {
    return `${minutesPast}min`;
  }

  const hoursPast = Math.floor(minutesPast / 60);

  if (hoursPast < 24) {
    return `${hoursPast}h`;
  }

  const daysPast = Math.floor(hoursPast / 24);

  if (daysPast < 30) {
    return `${daysPast}d`;
  }

  const monthsPast = Math.floor(daysPast / 30);

  if (monthsPast < 12) {
    return `${monthsPast}m`;
  }

  const yearsPast = Math.floor(monthsPast / 12);

  return `${yearsPast}y`;
}

export function compareLexicographically(a: string[], b: string[]) {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const comparison = a[i].localeCompare(b[i]);

    if (comparison !== 0) {
      return comparison;
    }
  }

  if (a.length > b.length) {
    return 1;
  }

  if (a.length < b.length) {
    return -1;
  }

  return 0;
}

export function faviconForUrl(url: string): string | null {
  try {
    const parsedUrl = new URL(url);
    return `${parsedUrl.protocol}//${parsedUrl.host}/favicon.ico`;
  } catch (error) {
    return null;
  }
}

export function purifyTitle({raw, default_}: {raw: string | null; default_: string}) {
  if (raw === null) {
    return default_;
  }

  let title = DOMPurify.sanitize(raw, {ALLOWED_TAGS: []}).trim();

  if (title.length === 0) {
    return default_;
  }

  title = hardenLinksSecurityAttributes(title);

  return title;
}

export function purifyBody({raw, default_}: {raw: string | null; default_: string}) {
  if (raw === null) {
    return default_;
  }

  let body = DOMPurify.sanitize(raw).trim();

  if (body.length === 0) {
    return default_;
  }

  body = removeNonFunctionalAttributes(body);
  body = hardenLinksSecurityAttributes(body);

  return body;
}

export function chooseTagByUsage({
  tagsCount,
  border,
  exclude
}: {
  tagsCount: {[key: string]: number};
  border: number;
  exclude: string[];
}) {
  if (Object.keys(tagsCount).length === 0) {
    return null;
  }

  if (!exclude) {
    exclude = [];
  }

  const tags = _.toPairs(tagsCount).sort((a: [string, number], b: [string, number]) => {
    if (a[1] === b[1]) {
      return a[0].localeCompare(b[0]);
    }

    return b[1] - a[1];
  });

  for (let i = 0; i < tags.length; i++) {
    if (exclude.includes(tags[i][0])) {
      continue;
    }

    if (tags[i][1] < border) {
      return tags[i][0];
    }
  }

  return tags[tags.length - 1][0];
}

export function countTags(entries: t.Entry[] | t.Rule[] | null) {
  if (!entries) {
    return {};
  }

  const tagsCount: {[key: string]: number} = {};

  for (const entry of entries) {
    for (const tag of entry.tags) {
      if (tag in tagsCount) {
        tagsCount[tag] += 1;
      } else {
        tagsCount[tag] = 1;
      }
    }
  }

  return tagsCount;
}

export function sortIdsList<ID extends string = string>({
  ids,
  storage,
  field,
  direction
}: {
  ids: ID[];
  storage: {[key: string]: any};
  field: string;
  direction: number;
}) {
  // Pre-map to avoid repeated lookups in the comparator
  // required for the cases when storage is reactive
  const mapped = ids.map((id) => {
    // @ts-ignore
    return {id, value: storage[id][field]};
  });

  mapped.sort((a: {id: ID; value: any}, b: {id: ID; value: any}) => {
    if (a.value === null && b.value === null) {
      return 0;
    }

    if (a.value === null) {
      return 1;
    }

    if (b.value === null) {
      return -1;
    }

    if (a.value < b.value) {
      return direction;
    }

    if (a.value > b.value) {
      return -direction;
    }

    return 0;
  });

  return mapped.map((x) => x.id);
}
