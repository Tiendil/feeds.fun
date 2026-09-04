import {describe, expect, it} from "vitest";

import {useAsyncAction} from "@/logic/asyncAction";

describe("useAsyncAction", () => {
  it("starts idle", () => {
    const action = useAsyncAction();

    expect(action.status).toBe("idle");
    expect(action.loading).toBe(false);
    expect(action.succeeded).toBe(false);
    expect(action.failed).toBe(false);
    expect(action.error).toBeNull();
  });

  it("tracks a successful action", async () => {
    const action = useAsyncAction();
    const resultPromise = action.run(async () => 42);

    expect(action.status).toBe("running");
    expect(action.loading).toBe(true);

    await expect(resultPromise).resolves.toBe(42);

    expect(action.status).toBe("succeeded");
    expect(action.loading).toBe(false);
    expect(action.succeeded).toBe(true);
  });

  it("tracks and rethrows a failed action", async () => {
    const action = useAsyncAction();
    const failure = new Error("failure");
    const resultPromise = action.run(async () => {
      throw failure;
    });

    await expect(resultPromise).rejects.toBe(failure);

    expect(action.status).toBe("failed");
    expect(action.failed).toBe(true);
    expect(action.error).toBe(failure);
  });

  it("ignores a stale failure after a newer action succeeds", async () => {
    const action = useAsyncAction();
    const staleFailure = new Error("stale failure");
    let rejectStaleAction!: (reason: unknown) => void;
    const staleAction = new Promise<string>((_resolve, reject) => {
      rejectStaleAction = reject;
    });
    const staleResultPromise = action.run(() => staleAction);

    await expect(action.run(async () => "current result")).resolves.toBe("current result");

    rejectStaleAction(staleFailure);
    await expect(staleResultPromise).rejects.toBe(staleFailure);
    expect(action.status).toBe("succeeded");
    expect(action.failed).toBe(false);
    expect(action.error).toBeNull();
  });

  it("ignores completion after reset", async () => {
    const action = useAsyncAction();
    let completeAction!: (result: string) => void;
    const pendingAction = new Promise<string>((resolve) => {
      completeAction = resolve;
    });
    const resultPromise = action.run(() => pendingAction);

    action.reset();
    completeAction("done");

    await expect(resultPromise).resolves.toBe("done");
    expect(action.status).toBe("idle");
    expect(action.loading).toBe(false);
    expect(action.succeeded).toBe(false);
  });
});
