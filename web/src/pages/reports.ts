import { Component, inject } from '@angular/core';
import { Api } from '../shared/api';
import { DateFilter } from '../shared/date-filter';
import { LoadStatus } from '../shared/feedback';
import { MoneyPipe, NumberPipe, ShortDatePipe } from '../shared/format';
import { Workspace } from '../shared/workspace';

@Component({
  imports: [DateFilter, LoadStatus, MoneyPipe, NumberPipe, ShortDatePipe],
  templateUrl: './reports.html',
})
export class Reports {
  private readonly api = inject(Api);
  protected readonly workspace = inject(Workspace);
  protected readonly report = this.api.load(() => this.api.report(this.workspace.reportDates()));
}
