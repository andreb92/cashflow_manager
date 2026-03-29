/**
 * Format a number as Italian currency: dot thousands separator, comma decimal, always 2 decimal places.
 * Example: 1234.5 → "1.234,50", 4500 → "4.500,00"
 * Uses manual regex to ensure consistent output regardless of ICU version.
 */
export const fmt = (n: number): string => {
  const [int, dec] = n.toFixed(2).split('.');
  return int.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + dec;
};
