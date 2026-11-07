import { Component, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Api, errorMessage } from '../shared/api';
import { moneyInput, parsePrice } from '../shared/format';
import { Icon } from '../shared/icon';
import { Product } from '../shared/models';
import { Workspace } from '../shared/workspace';

@Component({
  selector: 'app-product-form',
  imports: [FormsModule, Icon],
  templateUrl: './product-form.html',
})
export class ProductForm {
  readonly product = input<Product>();
  private readonly api = inject(Api);
  protected readonly workspace = inject(Workspace);
  protected readonly error = signal('');
  protected readonly categories = ['Mercearia', 'Casa e decoração', 'Papelaria', 'Utilidades', 'Acessórios', 'Outros'];
  protected readonly form = computed(() => {
    const product = this.product();
    return {
      sku: product?.sku ?? '',
      name: product?.name ?? '',
      category: product?.category ?? '',
      price: product ? moneyInput(product.price_cents) : '',
      stock: product?.stock ?? 0,
      active: product ? Boolean(product.active) : true,
    };
  });

  protected async save(): Promise<void> {
    if (this.workspace.busy()) return;
    this.workspace.busy.set(true);
    this.error.set('');
    try {
      const { sku, name, category, price, stock, active } = this.form();
      const price_cents = parsePrice(price);
      if (price_cents > 100000000) throw new Error('O preço máximo permitido é R$ 1.000.000,00.');
      const id = this.product()?.id ?? 0;
      await firstValueFrom(this.api.saveProduct(id, {
        sku: sku.trim(), name: name.trim(), category: category.trim(),
        price_cents, stock, active,
      }));
      this.workspace.modal.set(null);
      this.workspace.toast(id ? 'Produto atualizado.' : 'Produto cadastrado.');
      this.api.refresh();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.workspace.busy.set(false);
    }
  }
}
