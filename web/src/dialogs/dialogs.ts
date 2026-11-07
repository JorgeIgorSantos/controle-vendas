import { Component, ElementRef, afterRenderEffect, computed, inject, viewChild } from '@angular/core';
import { dateTime, saleId } from '../shared/format';
import { Icon } from '../shared/icon';
import { Workspace } from '../shared/workspace';
import { ProductForm } from './product-form';
import { Receipt } from './receipt';
import { SaleForm } from './sale-form';

@Component({
  selector: 'app-dialogs',
  imports: [Icon, ProductForm, Receipt, SaleForm],
  templateUrl: './dialogs.html',
})
export class Dialogs {
  protected readonly workspace = inject(Workspace);
  private readonly modal = viewChild.required<ElementRef<HTMLDialogElement>>('modal');
  private readonly confirmation = viewChild.required<ElementRef<HTMLDialogElement>>('confirmation');
  private readonly saleForm = viewChild(SaleForm);

  protected readonly heading = computed(() => {
    const modal = this.workspace.modal();
    switch (modal?.kind) {
      case 'product':
        return modal.product
          ? { title: 'Editar produto', subtitle: 'Atualize as informações do seu catálogo.' }
          : { title: 'Novo produto', subtitle: 'Informe os dados do produto.' };
      case 'sale':
        return { title: 'Nova venda', subtitle: 'Escolha os produtos, confira os valores e finalize.' };
      case 'receipt':
        return { title: 'Venda ' + saleId(modal.sale.id), subtitle: dateTime(modal.sale.created_at) + ' · Horário de Belém' };
      default:
        return null;
    }
  });

  constructor() {
    afterRenderEffect(() => {
      const modal = this.modal().nativeElement;
      const confirmation = this.confirmation().nativeElement;
      this.syncDialog(modal, !!this.workspace.modal());
      this.syncDialog(confirmation, !!this.workspace.confirmation());
    });
  }

  private syncDialog(dialog: HTMLDialogElement, open: boolean): void {
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }

  protected async close(event?: Event): Promise<void> {
    event?.preventDefault();
    if (this.workspace.busy()) return;
    if (this.saleForm()?.cart().length) {
      const confirmed = await this.workspace.confirm(
        'Sair desta venda?',
        'Os itens selecionados serão descartados. Nenhuma venda foi registrada.',
        'Descartar venda',
      );
      if (!confirmed) return;
    }
    this.workspace.modal.set(null);
  }
}
