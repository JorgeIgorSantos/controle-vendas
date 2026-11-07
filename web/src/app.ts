import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { Dialogs } from './dialogs/dialogs';
import { Icon, IconName } from './shared/icon';
import { Workspace } from './shared/workspace';

export const pages = [
  { path: 'products', name: 'Produtos', icon: 'box' },
  { path: 'sales', name: 'Vendas', icon: 'bag' },
  { path: 'reports', name: 'Relatórios', icon: 'chart' },
] as const satisfies readonly { path: string; name: string; icon: IconName }[];

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet, Dialogs, Icon],
  templateUrl: './app.html',
})
export class App {
  private readonly router = inject(Router);
  private readonly navigation = toSignal(this.router.events.pipe(filter(event => event instanceof NavigationEnd)));
  protected readonly workspace = inject(Workspace);
  protected readonly pages = pages;
  protected readonly breadcrumb = computed(() => {
    this.navigation();
    return this.router.routerState.snapshot.root.firstChild?.data['label'] ?? pages[0].name;
  });
  protected readonly date = new Intl.DateTimeFormat('pt-BR', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/Belem',
  }).format(new Date());

  protected skipToContent(event: MouseEvent, content: HTMLElement): void {
    event.preventDefault();
    content.focus();
  }
}
