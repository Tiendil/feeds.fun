import {ref, computed, reactive} from "vue";
import type {ComputedRef} from "vue";

export type State = "required" | "excluded" | "none";

interface ReturnTagsForEntity {
  (entity: any): string[];
}

export class Storage {
  requiredTags: {[key: string]: boolean};
  excludedTags: {[key: string]: boolean};
  selectedTags: ComputedRef<{[key: string]: boolean}>;
  hasSelectedTags: ComputedRef<boolean>;

  constructor() {
    this.requiredTags = reactive({});
    this.excludedTags = reactive({});

    this.selectedTags = computed(() => {
      return {...this.requiredTags, ...this.excludedTags};
    });

    this.hasSelectedTags = computed(() => {
      return Object.keys(this.selectedTags.value).length > 0;
    });
  }

  onTagStateChanged({tag, state}: {tag: string; state: State}) -> {fromState: State; toState: State} {
    if (state === "required") {
      this.requiredTags[tag] = true;
      if (this.excludedTags[tag]) {
        delete this.excludedTags[tag];
        return {"fromState": "excluded", "toState": "required"};
      }
      return {"fromState": "none", "toState": "required"};
    } else if (state === "excluded") {
      this.excludedTags[tag] = true;
      if (this.requiredTags[tag]) {
        delete this.requiredTags[tag];
        return {"fromState": "required", "toState": "excluded"};
      }
      return {"fromState": "none", "toState": "excluded"};
    } else if (state === "none") {
      if (this.requiredTags[tag]) {
        delete this.requiredTags[tag];
        return {"fromState": "required", "toState": "none"};
      }

      if (this.excludedTags[tag]) {
        delete this.excludedTags[tag];
        return {"fromState": "excluded", "toState": "none"};
      }

      return {"fromState": "none", "toState": "none"};
    } else {
      throw new Error(`Unknown tag state: ${state}`);
    }
  }

  onTagReversed({tag}: {tag: string}) {
    if (!(tag in this.selectedTags)) {
      return this.onTagStateChanged({tag: tag, state: "required"});
    } else if (this.requiredTags[tag]) {
      return this.onTagStateChanged({tag: tag, state: "excluded"});
    } else if (this.excludedTags[tag]) {
      return this.onTagStateChanged({tag: tag, state: "required"});
    } else {
      throw new Error(`Unknown tag state: ${tag}`);
    }
  }

  onTagClicked({tag}: {tag: string}) {
    if (tag in this.selectedTags) {
      return this.onTagStateChanged({tag: tag, state: "none"});
    } else {
      return this.onTagStateChanged({tag: tag, state: "required"});
    }
  }

  filterByTags(entities: any[], getTags: ReturnTagsForEntity) {
    let report = entities.slice();

    const requiredTags = Object.keys(this.requiredTags);

    report = report.filter((entity) => {
      for (const tag of getTags(entity)) {
        if (this.excludedTags[tag]) {
          return false;
        }
      }

      for (const tag of requiredTags) {
        if (!getTags(entity).includes(tag)) {
          return false;
        }
      }

      return true;
    });

    return report;
  }

  clear() {
    Object.keys(this.requiredTags).forEach((key) => {
      delete this.requiredTags[key];
    });

    Object.keys(this.excludedTags).forEach((key) => {
      delete this.excludedTags[key];
    });
  }
}
