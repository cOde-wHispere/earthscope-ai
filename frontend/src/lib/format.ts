export const number = (value: number, digits = 2) =>
  value.toLocaleString("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
export const signed = (value: number) =>
  `${value > 0 ? "+" : ""}${number(value, 3)}`;
export const pValue = (value: number) =>
  value === 0
    ? "Below numerical precision"
    : value < 0.001
      ? value.toExponential(2)
      : number(value, 4);
export const monthLabel = (date: string) =>
  new Intl.DateTimeFormat("en-GB", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));
export const monthName = (month: number) =>
  new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" }).format(
    new Date(Date.UTC(2000, month - 1, 1)),
  );
