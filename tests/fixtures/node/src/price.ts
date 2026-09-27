export interface LineItem {
  unitPrice: number;
  quantity: number;
}

/** Sum of line items in minor units, with an optional percentage discount. */
export function total(items: readonly LineItem[], discountPercent = 0): number {
  if (discountPercent < 0 || discountPercent > 100) {
    throw new RangeError("discountPercent must be between 0 and 100");
  }
  const gross = items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0);
  return Math.round(gross * (1 - discountPercent / 100));
}

export function formatPln(minor: number): string {
  return `${(minor / 100).toFixed(2)} zł`;
}
