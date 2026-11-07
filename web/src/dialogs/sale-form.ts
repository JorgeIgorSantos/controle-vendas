import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Api, errorMessage } from '../shared/api';
import { EmptyState } from '../shared/feedback';
import { MoneyPipe, NumberPipe, money, normalize, saleId } from '../shared/format';
import { Icon } from '../shared/icon';
import { Payment, Product, paymentNames } from '../shared/models';
import { Workspace } from '../shared/workspace';

interface CartItem {
  product: Product;
  quantity: number;
}

@Component({
  selector: 'app-sale-form',
  imports: [FormsModule, EmptyState, MoneyPipe, NumberPipe, Icon],
  templateUrl: './sale-form.html',
})
export class SaleForm {
  readonly products = input.required<Product[]>();
  readonly closeRequested = output();
  private readonly api = inject(Api);
  protected readonly workspace = inject(Workspace);
  readonly cart = signal<CartItem[]>([]);
  protected readonly error = signal('');
  protected readonly search = signal('');
  protected readonly form = { customer: '', payment_method: 'pix' as Payment };
  protected readonly paymentOptions = Object.entries(paymentNames);
  protected readonly catalog = computed(() => {
    const search = normalize(this.search());
    return this.products().filter(product =>
      normalize(`${product.name} ${product.sku} ${product.category}`).includes(search),
    );
  });
  protected readonly count = computed(() => this.cart().reduce((sum, item) => sum + item.quantity, 0));
  protected readonly total = computed(() => this.cart().reduce(
    (sum, item) => sum + item.product.price_cents * item.quantity, 0,
  ));
  protected changeQuantity(product: Product, delta: number): void {
    const quantity = (this.cart().find(item => item.product.id === product.id)?.quantity ?? 0) + delta;
    if (quantity > product.stock) {
      this.workspace.toast('A quantidade não pode superar o estoque disponível.', true);
      return;
    }
    this.setQuantity(product, quantity);
  }

  protected editQuantity(item: CartItem, input: HTMLInputElement): void {
    const quantity = input.valueAsNumber;
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > item.product.stock) {
      this.workspace.toast('Use uma quantidade inteira entre 1 e o estoque disponível.', true);
      input.value = String(item.quantity);
      return;
    }
    this.setQuantity(item.product, quantity);
  }

  protected setQuantity(product: Product, quantity: number): void {
    this.cart.update(items => {
      if (!quantity) return items.filter(item => item.product.id !== product.id);
      const changed = { product, quantity };
      return items.some(item => item.product.id === product.id)
        ? items.map(item => item.product.id === product.id ? changed : item)
        : [...items, changed];
    });
  }

  protected async save(): Promise<void> {
    if (this.workspace.busy() || !this.cart().length) return;
    this.workspace.busy.set(true);
    this.error.set('');
    try {
      const sale = await firstValueFrom(this.api.createSale({
        customer: this.form.customer.trim(),
        payment_method: this.form.payment_method,
        items: this.cart().map(item => ({ product_id: item.product.id, quantity: item.quantity })),
      }));
      this.workspace.modal.set({ kind: 'receipt', sale });
      this.workspace.toast(`Venda ${saleId(sale.id)} registrada. Total: ${money(sale.total_cents)}`);
      this.api.refresh();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.workspace.busy.set(false);
    }
  }
}
