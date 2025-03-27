import _ from "lodash";
import DOMPurify from "dompurify";

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

  return body;
}

export function chooseTagByUsage({tagsCount, border, exclude}: {tagsCount: {[key: string]: number}; percentile: number; exclude: string[]}) {

  if (Object.keys(tagsCount).length === 0) {
    return null;
  }

  if (!exclude) {
    exclude = [];
  }

  const tags = _.toPairs(tagsCount).sort((a, b) => {
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


export function sortIdsList<ID>({ids, storage, field, direction}: {ids: ID[]; storage: {[key: ID]: any}; field: string; direction: number}) {

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
};
