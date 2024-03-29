export type State = "required" | "excluded" | "none";

interface ReturnTagsForEntity {
  (entity: any): string[];
}

export class Storage {
  requiredTags: {[key: string]: boolean};
  excludedTags: {[key: string]: boolean};

  constructor() {
    this.requiredTags = {};
    this.excludedTags = {};
  }

  onTagStateChanged({tag, state}: {tag: string; state: State}) {
    if (state === "required") {
      this.requiredTags[tag] = true;
      this.excludedTags[tag] = false;
    } else if (state === "excluded") {
      this.excludedTags[tag] = true;
      this.requiredTags[tag] = false;
    } else if (state === "none") {
      this.excludedTags[tag] = false;
      this.requiredTags[tag] = false;
    } else {
      throw new Error(`Unknown tag state: ${state}`);
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
