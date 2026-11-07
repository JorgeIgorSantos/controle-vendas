export interface ProductData {
  sku: string;
  name: string;
  category: string;
  price_cents: number;
  stock: number;
}

export interface Product extends ProductData {
  id: number;
  active: boolean;
}

export const paymentNames = {
  pix: 'Pix',
  dinheiro: 'Dinheiro',
  credito: 'Cartão de crédito',
  debito: 'Cartão de débito',
};

export type Payment = keyof typeof paymentNames;

export interface SaleData {
  customer: string;
  payment_method: Payment;
}

interface Sale extends SaleData {
  discount_cents: number;
  notes: string;
  id: number;
  created_at: string;
  cancelled_at: string | null;
  status: 'completed' | 'cancelled';
  subtotal_cents: number;
  total_cents: number;
}

export interface SaleRow extends Sale {
  item_count: number;
}

export interface SaleDetail extends Sale {
  items: {
    id: number;
    name: string;
    sku: string;
    quantity: number;
    unit_price_cents: number;
    total_cents: number;
  }[];
}

export interface DateRange {
  from: string;
  to: string;
}

export interface Report extends DateRange {
  summary: { sale_count: number; total_cents: number };
}
