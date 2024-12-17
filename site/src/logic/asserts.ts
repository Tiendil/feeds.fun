export function defined<T>(value: T | null | undefined, name?: string): asserts value is T {
  if (value === null || value === undefined) {
    throw new Error(`${name ?? "Value"} is null or undefined`);
  }
}
