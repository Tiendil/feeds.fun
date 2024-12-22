import { ref, computed, reactive } from 'vue';


export type State = "required" | "excluded" | "none";

interface ReturnTagsForEntity {
  (entity: any): string[];
}

export class Storage {
  requiredTags: {[key: string]: boolean};
  excludedTags: {[key: string]: boolean};
  selectedTags: {[key: string]: boolean};
  hasSelectedTags: boolean;

  constructor() {
    this.requiredTags = reactive({});
    this.excludedTags = reactive({});

    this.selectedTags = computed(() => {
      return {...this.requiredTags, ...this.excludedTags};
    });

    this.hasSelectedTags = computed(() => {
      return Object.keys(this.selectedTags).length > 0;
    });
  }

  onTagStateChanged({tag, state}: {tag: string; state: State}) {
    if (state === "required") {
      this.requiredTags[tag] = true;
      if (this.excludedTags[tag]) {
        delete this.excludedTags[tag];
      }
    } else if (state === "excluded") {
      this.excludedTags[tag] = true;
      if (this.requiredTags[tag]) {
        delete this.requiredTags[tag];
      }
    } else if (state === "none") {
      if (this.requiredTags[tag]) {
        delete this.requiredTags[tag];
      }

      if (this.excludedTags[tag]) {
        delete this.excludedTags[tag];
      }

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

  clear() {
    Object.assign(this.requiredTags, {});
    Object.assign(this.excludedTags, {});
  }
}
