import { Component, computed, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { Api } from '../shared/api';
import { EmptyState, LoadStatus } from '../shared/feedback';
import { MoneyPipe, NumberPipe, normalize } from '../shared/format';
import { Icon } from '../shared/icon';
import { Product } from '../shared/models';
import { Workspace } from '../shared/workspace';

@Component({
  imports: [FormsModule, EmptyState, LoadStatus, MoneyPipe, NumberPipe, Icon],
  templateUrl: './products.html',
})
export class Products {
  private readonly api = inject(Api);
  protected readonly workspace = inject(Workspace);
  protected readonly products = this.api.load(() => this.api.products());
  protected readonly filtered = computed(() => {
    const search = normalize(this.workspace.productSearch());
    return this.products().data?.filter(product =>
      normalize(`${product.sku} ${product.name} ${product.category}`).includes(search),
    ) ?? [];
  });
  private deleting = false;

  protected async deleteProduct(product: Product): Promise<void> {
    if (this.deleting) return;
    this.deleting = true;
    try {
      const confirmed = await this.workspace.confirm(
        'Excluir este produto?',
        `${product.name} será removido do catálogo. Produtos com vendas no histórico devem ser desativados.`,
        'Excluir produto',
      );
      if (!confirmed) return;
      await firstValueFrom(this.api.deleteProduct(product.id));
      this.workspace.toast('Produto excluído.');
      this.api.refresh();
    } catch (error) {
      this.workspace.showError(error);
    } finally {
      this.deleting = false;
    }
  }
}
