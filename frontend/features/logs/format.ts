const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Compact view count, or an em dash when the count is unknown. */
export function formatViews(count: number | null): string {
  if (count == null) return "—";
  if (count >= 1_000_000) {
    const millions = count / 1_000_000;
    const text = millions >= 10 ? millions.toFixed(0) : millions.toFixed(1);
    return `${text.replace(/\.0$/, "")}M`;
  }
  if (count >= 1_000) return `${Math.round(count / 1_000)}K`;
  return String(count);
}

/** Local date and time for an ISO timestamp, or an em dash when it is missing. */
export function formatWhen(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const month = MONTHS[date.getMonth()] ?? "";
  return `${date.getDate()} ${month}, ${hours}:${minutes}`;
}
