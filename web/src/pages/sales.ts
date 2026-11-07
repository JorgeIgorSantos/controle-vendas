import { Component, inject } from '@angular/core';
import { Api } from '../shared/api';
import { DateFilter } from '../shared/date-filter';
import { LoadStatus } from '../shared/feedback';
import { NumberPipe } from '../shared/format';
import { Icon } from '../shared/icon';
import { SalesTable } from '../shared/sales-table';
import { Workspace } from '../shared/workspace';

@Component({
  imports: [DateFilter, LoadStatus, NumberPipe, Icon, SalesTable],
  templateUrl: './sales.html',
})
export class Sales {
  private readonly api = inject(Api);
  protected readonly workspace = inject(Workspace);
  protected readonly sales = this.api.load(() => this.api.sales(this.workspace.salesDates(), this.workspace.salesSearch()));

  protected search(event: SubmitEvent, term: string): void {
    event.preventDefault();
    this.workspace.salesSearch.set(term.trim());
  }
}
