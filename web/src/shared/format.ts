import { Pipe } from '@angular/core';

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const number = new Intl.NumberFormat('pt-BR');
const localDateTime = new Intl.DateTimeFormat('pt-BR', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Belem',
});

export function money(cents: number): string {
  return currency.format(cents / 100);
}

@Pipe({ name: 'brl' })
export class MoneyPipe {
  transform = money;
}

@Pipe({ name: 'brNumber' })
export class NumberPipe {
  transform(value: number): string { return number.format(value); }
}

@Pipe({ name: 'belemTime' })
export class LocalTimePipe {
  transform = dateTime;
}

@Pipe({ name: 'brDate' })
export class ShortDatePipe {
  transform = shortDate;
}

@Pipe({ name: 'saleId' })
export class SaleIdPipe {
  transform = saleId;
}

export function saleId(id: number): string {
  return '#' + String(id).padStart(4, '0');
}

export function dateTime(iso: string): string {
  return localDateTime.format(new Date(iso));
}

export function todayISO(): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Belem', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts();
  const part = (type: string) => parts.find(item => item.type === type)?.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

export function addDays(day: string, amount: number): string {
  const date = new Date(day + 'T12:00:00Z');
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

export function recentDates(days = 30) {
  const to = todayISO();
  return { from: addDays(to, 1 - days), to };
}

export function shortDate(day: string): string {
  const [year, month, date] = day.split('-');
  return `${date}/${month}/${year}`;
}

export function normalize(text: string): string {
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

export function moneyInput(cents: number): string {
  return (cents / 100).toFixed(2).replace('.', ',');
}

export function parsePrice(value: string): number {
  const clean = value.trim();
  if (!/^\d{1,13}([,.]\d{1,2})?$/.test(clean)) {
    throw new Error('Informe o valor com até duas casas decimais, por exemplo: 24,90.');
  }
  const [whole, fraction = ''] = clean.replace(',', '.').split('.');
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
  if (cents === 0) throw new Error('O preço deve ser maior que zero.');
  return cents;
}
