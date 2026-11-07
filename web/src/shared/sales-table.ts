import { Component, inject, input } from '@angular/core';
import { EmptyState } from './feedback';
import { LocalTimePipe, MoneyPipe, SaleIdPipe } from './format';
import { Icon } from './icon';
import { SaleRow, paymentNames } from './models';
import { Workspace } from './workspace';

@Component({
  selector: 'app-sales-table',
  imports: [EmptyState, LocalTimePipe, MoneyPipe, SaleIdPipe, Icon],
  templateUrl: './sales-table.html',
})
export class SalesTable {
  readonly sales = input.required<SaleRow[]>();
  protected readonly paymentNames = paymentNames;
  protected readonly workspace = inject(Workspace);
}
