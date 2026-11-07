import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Api, errorMessage } from './api';
import { recentDates } from './format';
import { Product, SaleDetail } from './models';

export type Modal =
  | { kind: 'product'; product?: Product }
  | { kind: 'sale'; products: Product[] }
  | { kind: 'receipt'; sale: SaleDetail };

interface Confirmation {
  title: string;
  message: string;
  action: string;
  resolve: (confirmed: boolean) => void;
}

@Injectable({ providedIn: 'root' })
export class Workspace {
  private readonly api = inject(Api);
  private opening = false;
  private toastId = 0;
  readonly modal = signal<Modal | null>(null);
  readonly busy = signal(false);
  readonly confirmation = signal<Confirmation | null>(null);
  readonly toasts = signal<{ id: number; message: string; error: boolean }[]>([]);
  readonly productSearch = signal('');
  readonly salesSearch = signal('');
  readonly salesDates = signal(recentDates());
  readonly reportDates = signal(recentDates());

  toast(message: string, error = false): void {
    const id = ++this.toastId;
    this.toasts.update(items => [...items, { id, message, error }]);
    setTimeout(() => this.toasts.update(items => items.filter(item => item.id !== id)), 6000);
  }

  showError(error: unknown): void {
    this.toast(errorMessage(error), true);
  }

  confirm(title: string, message: string, action: string): Promise<boolean> {
    if (this.confirmation()) return Promise.resolve(false);
    return new Promise(resolve => this.confirmation.set({ title, message, action, resolve }));
  }

  finishConfirmation(confirmed: boolean): void {
    const confirmation = this.confirmation();
    this.confirmation.set(null);
    confirmation?.resolve(confirmed);
  }

  async openProduct(id?: number): Promise<void> {
    await this.open(async () => ({
      kind: 'product',
      product: id ? await firstValueFrom(this.api.product(id)) : undefined,
    }));
  }

  async openSale(): Promise<void> {
    await this.open(async () => ({ kind: 'sale', products: await firstValueFrom(this.api.products(true)) }));
  }

  async openReceipt(id: number): Promise<void> {
    await this.open(async () => ({ kind: 'receipt', sale: await firstValueFrom(this.api.sale(id)) }));
  }

  private async open(load: () => Promise<Modal>): Promise<void> {
    if (this.opening || this.modal()) return;
    this.opening = true;
    try {
      this.modal.set(await load());
    } catch (error) {
      this.showError(error);
    } finally {
      this.opening = false;
    }
  }
}
