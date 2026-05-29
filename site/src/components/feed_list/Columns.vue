<template>
  <div class="flex">
    <div class="flex-shrink-0 w-4 mr-2 cursor-default">
      <slot name="action" />
    </div>

    <div class="flex-shrink-0 w-16 cursor-default text-right">
      <slot name="checked" />
    </div>

    <div class="flex-shrink-0 w-16 cursor-default text-right">
      <slot name="added" />
    </div>

    <div class="flex-shrink-0 w-14 cursor-default text-right pr-1">
      <slot name="rate" />
    </div>

    <div class="flex-shrink-0 w-8 cursor-default text-right pr-1">
      <slot name="favicon" />
    </div>

    <div class="flex-grow min-w-0">
      <slot name="main" />
    </div>
  </div>
</template>
