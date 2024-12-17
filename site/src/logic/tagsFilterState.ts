export type State = "required" | "excluded" | "none";

interface ReturnTagsForEntity {
  (entity: any): string[];
}

export class Storage {
  requiredTags: {[key: string]: boolean};
  excludedTags: {[key: string]: boolean};
  selectedTags: {[key: string]: boolean}; // TODO: make calculated property?

  constructor() {
    this.requiredTags = {};
    this.excludedTags = {};
    this.selectedTags = {};
  }

  onTagStateChanged({tag, state}: {tag: string; state: State}) {
    if (state === "required") {
      this.requiredTags[tag] = true;
      this.excludedTags[tag] = false;
      this.selectedTags[tag] = true;
    } else if (state === "excluded") {
      this.excludedTags[tag] = true;
      this.requiredTags[tag] = false;
      this.selectedTags[tag] = true;
    } else if (state === "none") {
      this.excludedTags[tag] = false;
      this.requiredTags[tag] = false;
      delete this.selectedTags[tag];
    } else {
      throw new Error(`Unknown tag state: ${state}`);
    }
  }

  onTagReversed({tag}: {tag: string}) {
    if (!(tag in this.selectedTags)) {
      this.onTagStateChanged({tag: tag, state: "required"});
    } else if (this.requiredTags[tag]) {
      this.onTagStateChanged({tag: tag, state: "excluded"});
    } else if (this.excludedTags[tag]) {
      this.onTagStateChanged({tag: tag, state: "required"});
    } else {
      throw new Error(`Unknown tag state: ${tag}`);
    }
  }

  onTagClicked({tag}: {tag: string}) {
    if (tag in this.selectedTags) {
      this.onTagStateChanged({tag: tag, state: "none"});
    } else {
      this.onTagStateChanged({tag: tag, state: "required"});
    }
  }

  filterByTags(entities: any[], getTags: ReturnTagsForEntity) {
    let report = entities.slice();

    report = report.filter((entity) => {
      for (const tag of getTags(entity)) {
        if (this.excludedTags[tag]) {
          return false;
        }
      }
      return true;
    });

    report = report.filter((entity) => {
      for (const tag of Object.keys(this.requiredTags)) {
        if (this.requiredTags[tag] && !getTags(entity).includes(tag)) {
          return false;
        }
      }
      return true;
    });

    return report;
  }
}
