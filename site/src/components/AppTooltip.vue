<template>
  <span
    ref="root"
    class="contents"
    @pointerenter="onPointerEnter"
    @pointerleave="onPointerLeave"
    @pointerdown="onPointerDown"
    @focusin="onFocusIn"
    @focusout="onFocusOut"
    @keydown.esc="dismiss">
    <slot />

    <Teleport to="body">
      <div
        v-if="visible"
        ref="tooltip"
        class="pointer-events-none fixed z-[100] max-h-[calc(100vh-2rem)] w-max max-w-[calc(100vw-2rem)] overflow-hidden whitespace-normal rounded bg-slate-900 px-3 py-2 text-left text-xs font-normal leading-relaxed text-white shadow-lg sm:max-w-sm"
        :class="`tooltip-${resolvedSide}`"
        :style="position">
        <slot name="content">{{ text }}</slot>
      </div>
    </Teleport>
  </span>
</template>

<script lang="ts" setup>
  import {computed, nextTick, onUnmounted, ref, useSlots, useTemplateRef, watch} from "vue";

  type TooltipPlacement = "top" | "top-start" | "top-end" | "bottom" | "bottom-start" | "bottom-end";
  type TooltipSide = "top" | "bottom";
  type TooltipAlignment = "start" | "center" | "end";

  const tooltipGapPx = 8;
  const tooltipViewportPaddingPx = 8;

  const properties = withDefaults(
    defineProps<{
      text?: string;
      placement?: TooltipPlacement;
    }>(),
    {
      text: "",
      placement: "top"
    }
  );

  const slots = useSlots();
  const root = useTemplateRef<HTMLElement>("root");
  const tooltip = useTemplateRef<HTMLElement>("tooltip");
  const hovered = ref(false);
  const focused = ref(false);
  const touched = ref(false);
  const dismissed = ref(false);
  const resolvedSide = ref<TooltipSide>("top");
  const position = ref<Record<string, string>>({});

  const hasContent = computed(() => properties.text.length > 0 || slots.content !== undefined);
  const visible = computed(
    () => hasContent.value && !dismissed.value && (hovered.value || focused.value || touched.value)
  );
  const preferredPlacement = computed(() => {
    const [side, alignment = "center"] = properties.placement.split("-");

    return {
      side: side as TooltipSide,
      alignment: alignment as TooltipAlignment
    };
  });

  function triggerElement(): Element | null {
    return root.value?.firstElementChild ?? null;
  }

  function updatePosition(): void {
    const trigger = triggerElement();

    if (trigger === null || tooltip.value === null) {
      return;
    }

    const triggerRect = trigger.getBoundingClientRect();
    const tooltipRect = tooltip.value.getBoundingClientRect();
    let side = preferredPlacement.value.side;

    const topSpace = triggerRect.top - tooltipViewportPaddingPx;
    const bottomSpace = window.innerHeight - triggerRect.bottom - tooltipViewportPaddingPx;

    if (side === "top" && tooltipRect.height + tooltipGapPx > topSpace && bottomSpace > topSpace) {
      side = "bottom";
    } else if (side === "bottom" && tooltipRect.height + tooltipGapPx > bottomSpace && topSpace > bottomSpace) {
      side = "top";
    }

    resolvedSide.value = side;
    let left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2;

    if (preferredPlacement.value.alignment === "start") {
      left = triggerRect.left;
    } else if (preferredPlacement.value.alignment === "end") {
      left = triggerRect.right - tooltipRect.width;
    }

    left = Math.min(
      Math.max(left, tooltipViewportPaddingPx),
      Math.max(tooltipViewportPaddingPx, window.innerWidth - tooltipRect.width - tooltipViewportPaddingPx)
    );

    position.value = {
      left: `${left}px`,
      "--tooltip-gap": `${tooltipGapPx}px`,
      "--tooltip-viewport-padding": `${tooltipViewportPaddingPx}px`,
      "--tooltip-trigger-top": `${triggerRect.top}px`,
      "--tooltip-trigger-bottom": `${triggerRect.bottom}px`,
      "--tooltip-height": `${tooltipRect.height}px`
    };
  }

  function onPointerEnter(event: PointerEvent): void {
    if (event.pointerType === "touch") {
      return;
    }

    dismissed.value = false;
    hovered.value = true;
  }

  function onPointerLeave(event: PointerEvent): void {
    if (event.pointerType === "touch") {
      return;
    }

    hovered.value = false;

    if (!focused.value) {
      dismissed.value = false;
    }
  }

  function onPointerDown(event: PointerEvent): void {
    if (event.pointerType !== "touch") {
      return;
    }

    if (touched.value) {
      touched.value = false;
      dismissed.value = true;
      return;
    }

    dismissed.value = false;
    touched.value = true;
  }

  function onFocusIn(): void {
    dismissed.value = false;
    focused.value = true;
  }

  function onFocusOut(): void {
    void nextTick(() => {
      focused.value = root.value?.contains(document.activeElement) ?? false;
      dismissed.value = false;
    });
  }

  function dismiss(): void {
    touched.value = false;
    dismissed.value = true;
  }

  function dismissOnOutsidePointer(event: PointerEvent): void {
    if (root.value?.contains(event.target as Node)) {
      return;
    }

    touched.value = false;
    dismissed.value = true;
  }

  function addPositionListeners(): void {
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    document.addEventListener("pointerdown", dismissOnOutsidePointer);
  }

  function removePositionListeners(): void {
    window.removeEventListener("resize", updatePosition);
    window.removeEventListener("scroll", updatePosition, true);
    document.removeEventListener("pointerdown", dismissOnOutsidePointer);
  }

  watch(
    visible,
    async (isVisible) => {
      removePositionListeners();

      if (!isVisible) {
        return;
      }

      addPositionListeners();
      await nextTick();
      updatePosition();
    },
    {flush: "post"}
  );

  onUnmounted(removePositionListeners);
</script>

<style scoped>
  .tooltip-top {
    --tooltip-preferred-top: calc(var(--tooltip-trigger-top) - var(--tooltip-height) - var(--tooltip-gap));
  }

  .tooltip-bottom {
    --tooltip-preferred-top: calc(var(--tooltip-trigger-bottom) + var(--tooltip-gap));
  }

  .tooltip-top,
  .tooltip-bottom {
    top: clamp(
      var(--tooltip-viewport-padding),
      var(--tooltip-preferred-top),
      calc(100vh - var(--tooltip-height) - var(--tooltip-viewport-padding))
    );
  }
</style>
