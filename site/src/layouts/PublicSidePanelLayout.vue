<template>
  <div class="ffun-side-panel-layout">
    <div class="ffun-side-panel">
      <div class="ffun-page-header">
        <div class="ffun-page-header-title">
          <slot name="main-header"></slot>
        </div>
      </div>

      <hr />

      <ul class="ffun-side-panel-controls-list">
        <li v-if="hasSideMenuItem(1)">
          <slot name="side-menu-item-1"></slot>
        </li>

        <li v-if="hasSideMenuItem(2)">
          <slot name="side-menu-item-2"></slot>
        </li>

        <li v-if="hasSideMenuItem(3)">
          <slot name="side-menu-item-3"></slot>
        </li>

        <li v-if="hasSideMenuItem(4)">
          <slot name="side-menu-item-4"></slot>
        </li>

        <li v-if="hasSideMenuItem(5)">
          <slot name="side-menu-item-5"></slot>
        </li>
      </ul>

      <hr v-if="hasSideFooter" />

      <slot name="side-footer"></slot>
    </div>

    <div class="ffun-body-panel">
      <div class="ffun-page-header">
        <div class="ffun-page-header-left-block">
          <page-header-external-links :show-api="true" />
        </div>

        <div class="ffun-page-header-right-block">
        </div>
      </div>

      <hr class="my-2 border-slate-400" />

      <main class="mb-4 px-4 min-h-screen">
        <slot></slot>
      </main>

      <footer>
        <slot name="main-footer"></slot>
      </footer>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed, useSlots} from "vue";

  const slots = useSlots();

  const hasSideFooter = computed(() => {
    return !!slots["side-footer"];
  });

  function hasSideMenuItem(index: number) {
    return !!slots[`side-menu-item-${index}`];
  }
</script>
