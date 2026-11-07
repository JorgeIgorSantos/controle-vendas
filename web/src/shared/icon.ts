import { Component, input } from '@angular/core';

export type IconName = 'box' | 'bag' | 'chart' | 'plus' | 'search' | 'edit' | 'trash' | 'close' | 'eye' | 'check' | 'refresh';

@Component({
  selector: 'app-icon',
  templateUrl: './icon.html',
})
export class Icon {
  readonly name = input.required<IconName>();
  readonly size = input(18);
}
