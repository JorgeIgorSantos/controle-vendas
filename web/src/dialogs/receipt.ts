import { Component, inject, input } from '@angular/core';
import { LocalTimePipe, MoneyPipe, NumberPipe } from '../shared/format';
import { SaleDetail, paymentNames } from '../shared/models';
import { Workspace } from '../shared/workspace';

@Component({
  selector: 'app-receipt',
  imports: [LocalTimePipe, MoneyPipe, NumberPipe],
  templateUrl: './receipt.html',
})
export class Receipt {
  readonly sale = input.required<SaleDetail>();
  protected readonly workspace = inject(Workspace);
  protected readonly paymentNames = paymentNames;
}
