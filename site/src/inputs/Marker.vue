<template>
<div style="display: inline-block;">

<template v-if="hasMarker">
  <a href="#" class="marked" @click.prevent="unmark()">{{onText}}</a>
</template>

<template v-else>
  <a href="#" class="unmarked" @click.prevent="mark()">{{offText}}</a>
</template>

</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as api from "@/logic/api";
import * as e from "@/logic/enums";
import * as t from "@/logic/types";

const properties = defineProps<{marker: e.Marker,
                                entry: t.Entry,
                                onText: string,
                                offText: string}>();

const newHas = ref(null);

const hasMarker = computed(() => {
    if (newHas.value !== null) {
        return newHas.value;
    }

    return properties.entry.markers.includes(properties.marker);
});

function mark() {
    newHas.value = true;
    api.setMarker({entryId: properties.entry.id, marker: properties.marker});
}

function unmark() {
    newHas.value = false;
    api.removeMarker({entryId: properties.entry.id, marker: properties.marker});
}


</script>

<style scoped>

.marked {
    color: #2e8f2e;
    font-weight: bold;
    text-decoration: none;
}


.unmarked {
    color: purple;
    /* font-weight: bold; */
    text-decoration: none;
}
</style>
