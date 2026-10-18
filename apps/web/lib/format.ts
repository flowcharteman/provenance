// Groups digits as a string so large or fractional values keep exact precision.
export function formatValue(raw: string): string {
  const match = /^(-?)(\d+)(\.\d+)?$/.exec(raw);
  if (!match) {
    return raw;
  }
  const [, sign, integer, fraction = ""] = match;
  return `${sign}${integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}${fraction}`;
}
