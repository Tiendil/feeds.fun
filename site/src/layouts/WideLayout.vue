<template>
  <div class="flex justify-center h-screen">
    <div class="flex flex-col justify-start items-center text-center p-4">
      <header>
        <h1>
          <slot name="header"></slot>
        </h1>
      </header>

      <main>
        <slot></slot>
      </main>

      <footer>
        <slot name="footer"></slot>
      </footer>
    </div>
  </div>
</template>

<script lang="ts" setup></script>
