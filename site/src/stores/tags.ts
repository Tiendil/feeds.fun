import {computed, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";

import type * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import {Timer} from "@/logic/timer";
import {computedAsync} from "@vueuse/core";

export const useTagsStore = defineStore("tagsStore", () => {
  const tags = ref<{[key: string]: t.TagInfo}>({});
  const requestedTags = ref<{[key: string]: boolean}>({});

  const firstTimeTagsLoading = ref(true);

  function registerTag(tag: t.TagInfo) {
    tags.value[tag.uid] = tag;
  }

  function requestTagInfo({tagUid}: {tagUid: string}) {
    if (tagUid in tags.value) {
      return;
    }

    requestedTags.value[tagUid] = true;
  }

  async function loadTagsInfo() {
    const uids = Object.keys(requestedTags.value);

    if (uids.length === 0) {
      return;
    }

    const tagsInfo = await api.getTagsInfo({uids: uids});

    for (const uid in tagsInfo) {
      const tag = tagsInfo[uid];
      registerTag(tag);
    }

    requestedTags.value = {};
  }

  const requestedTagsTimer = new Timer(loadTagsInfo, 1000);

  requestedTagsTimer.start();

  return {
    tags,
    requestTagInfo
  };
});
