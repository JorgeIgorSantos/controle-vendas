import { Component, inject, input, output } from '@angular/core';
import { DateRange } from './models';
import { Workspace } from './workspace';

@Component({
  selector: 'app-date-filter',
  template: `
    <form class="date-filter" aria-label="Filtrar por período" [id]="prefix() + '-dates'" (submit)="apply($event, from.value, to.value)">
      <label [for]="prefix() + '-from'">De</label>
      <input #from type="date" [id]="prefix() + '-from'" [value]="dates().from"
        min="1900-01-01" max="9999-12-31" required aria-label="Data inicial">
      <label [for]="prefix() + '-to'">até</label>
      <input #to type="date" [id]="prefix() + '-to'" [value]="dates().to"
        min="1900-01-01" max="9999-12-31" required aria-label="Data final">
      <button class="button small" type="submit">Aplicar</button>
    </form>
  `,
})
export class DateFilter {
  readonly prefix = input.required<string>();
  readonly dates = input.required<DateRange>();
  readonly applyDates = output<DateRange>();
  private readonly workspace = inject(Workspace);

  protected apply(event: SubmitEvent, from: string, to: string): void {
    event.preventDefault();
    if (from > to) {
      this.workspace.toast('A data inicial deve ser anterior ou igual à data final.', true);
      return;
    }
    this.applyDates.emit({ from, to });
  }
}
