import {computed, reactive, readonly, ref} from "vue";

export type AsyncActionStatus = "idle" | "running" | "succeeded" | "failed";

export function useAsyncAction() {
  const currentStatus = ref<AsyncActionStatus>("idle");
  const currentError = ref<unknown>(null);
  let revision = 0;

  const loading = computed(() => currentStatus.value === "running");
  const succeeded = computed(() => currentStatus.value === "succeeded");
  const failed = computed(() => currentStatus.value === "failed");

  async function run<Result>(action: () => Promise<Result>): Promise<Result> {
    const actionRevision = ++revision;

    currentStatus.value = "running";
    currentError.value = null;

    try {
      const result = await action();

      if (actionRevision === revision) {
        currentStatus.value = "succeeded";
      }

      return result;
    } catch (caughtError) {
      if (actionRevision === revision) {
        currentStatus.value = "failed";
        currentError.value = caughtError;
      }

      throw caughtError;
    }
  }

  function reset(): void {
    ++revision;
    currentStatus.value = "idle";
    currentError.value = null;
  }

  return readonly(
    reactive({
      status: currentStatus,
      loading,
      succeeded,
      failed,
      error: currentError,
      run,
      reset
    })
  );
}
