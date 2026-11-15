// A full record renders hundreds of cells. Reuse formatters while preserving
// the existing locale, precision and UTC labels; no scientific values change.
const numberFormats = new Map<number, Intl.NumberFormat>();
export const number = (value: number, digits = 2) => {
  let formatter = numberFormats.get(digits);
  if (!formatter) {
    formatter = new Intl.NumberFormat("en-GB", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
    numberFormats.set(digits, formatter);
  }
  return formatter.format(value);
};
const monthYearFormat = new Intl.DateTimeFormat("en-GB", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const monthFormat = new Intl.DateTimeFormat("en-GB", {
  month: "short",
  timeZone: "UTC",
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
  monthYearFormat.format(new Date(`${date}T00:00:00Z`));
export const monthName = (month: number) =>
  monthFormat.format(new Date(Date.UTC(2000, month - 1, 1)));
