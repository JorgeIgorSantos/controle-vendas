import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { Observable, catchError, map, of, startWith, switchMap } from 'rxjs';
import { DateRange, Product, ProductData, Report, SaleData, SaleDetail, SaleRow } from './models';

export function errorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) {
      return 'Não foi possível carregar os dados. Verifique a conexão e tente novamente.';
    }
    return error.error?.error || 'Não foi possível concluir a operação.';
  }
  return error instanceof Error ? error.message : 'Não foi possível concluir a operação.';
}

interface RequestState<T> {
  data?: T;
  error?: string;
}

@Injectable({ providedIn: 'root' })
export class Api {
  private readonly http = inject(HttpClient);
  private readonly revision = signal(0);

  refresh(): void { this.revision.update(value => value + 1); }

  products(activeOnly = false) {
    return this.http.get<Product[]>('/api/products', activeOnly ? { params: { status: 'active' } } : {});
  }

  product(id: number) { return this.http.get<Product>(`/api/products/${id}`); }

  saveProduct(id: number, product: ProductData & { active: boolean }) {
    return id
      ? this.http.put<Product>(`/api/products/${id}`, product)
      : this.http.post<Product>('/api/products', product);
  }

  deleteProduct(id: number) { return this.http.delete(`/api/products/${id}`); }

  sales(dates: DateRange, search: string) {
    return this.http.get<SaleRow[]>('/api/sales', { params: { ...dates, search } });
  }

  sale(id: number) { return this.http.get<SaleDetail>(`/api/sales/${id}`); }

  createSale(sale: SaleData & { items: { product_id: number; quantity: number }[] }) {
    return this.http.post<SaleDetail>('/api/sales', sale);
  }

  report(dates: DateRange) {
    return this.http.get<Report>('/api/reports', { params: { ...dates } });
  }

  load<T>(request: () => Observable<T>) {
    const source = computed(() => {
      this.revision();
      return request();
    });
    const loading: RequestState<T> = {};
    return toSignal(toObservable(source).pipe(
      switchMap(query => query.pipe(
        map((data): RequestState<T> => ({ data })),
        catchError(error => of<RequestState<T>>({ error: errorMessage(error) })),
        startWith(loading),
      )),
    ), { initialValue: loading });
  }
}
