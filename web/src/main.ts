import { provideHttpClient } from '@angular/common/http';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, withHashLocation } from '@angular/router';
import { App, pages } from './app';
import { Products } from './pages/products';
import { Reports } from './pages/reports';
import { Sales } from './pages/sales';

const components = { products: Products, sales: Sales, reports: Reports };

bootstrapApplication(App, {
  providers: [
    provideHttpClient(),
    provideRouter([
      ...pages.map(({ path, name }) => ({
        path, component: components[path], title: name + ' — Venda.', data: { label: name },
      })),
      { path: '**', redirectTo: 'products' },
    ], withHashLocation()),
  ],
}).catch(error => console.error(error));
