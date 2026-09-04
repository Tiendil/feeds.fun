<template>
  <nav>
    <p class="ui-section-nav-title">On this page</p>

    <ul class="ui-section-nav-list">
      <li
        v-for="section in sections"
        :key="section.id"
        class="ui-section-nav-item">
        <a
          :href="`#${section.id}`"
          class="ui-section-nav-link">
          {{ section.title }}
        </a>
      </li>
    </ul>
  </nav>
</template>

<script lang="ts" setup>
  defineProps<{
    sections: readonly {
      readonly id: string;
      readonly title: string;
    }[];
  }>();
</script>
