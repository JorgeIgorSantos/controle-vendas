import { Component, inject, input } from '@angular/core';
import { Api } from './api';
import { Icon } from './icon';

@Component({
  selector: 'app-load-status',
  imports: [Icon],
  template: `
    @if (error()) {
      <div class="error-panel">
        <h2>Não foi possível carregar os dados</h2>
        <p>{{ error() }}</p>
        <button class="button" (click)="api.refresh()"><app-icon name="refresh" [size]="15" />Tentar novamente</button>
      </div>
    } @else {
      <div class="loading" role="status">Carregando…</div>
    }
  `,
})
export class LoadStatus {
  readonly error = input<string>();
  protected readonly api = inject(Api);
}

@Component({
  selector: 'app-empty-state',
  imports: [Icon],
  template: `
    <div class="empty-state" [class.compact]="compact()">
      <app-icon name="box" [size]="32" />
      <h3>{{ heading() }}</h3>
      <p>{{ description() }}</p>
    </div>
  `,
})
export class EmptyState {
  readonly heading = input.required<string>();
  readonly description = input.required<string>();
  readonly compact = input(false);
}
