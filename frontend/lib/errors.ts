/** A sentence safe to show in the UI for a failed request or player call. */
export function errorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    const message = caught.message.trim();
    if (message) return message;
  }
  if (typeof caught === "string") {
    const message = caught.trim();
    if (message) return message;
  }
  return "Something went wrong. Try again.";
}
