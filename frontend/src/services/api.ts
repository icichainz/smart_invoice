import axios, { AxiosResponse } from 'axios';
import {
  Client,
  ClientCreate,
  Invoice,
  InvoiceCreate,
  InvoiceItem,
  InvoiceItemCreate,
  PaginatedResponse,
  ApiResponse,
  PublicInvoice
} from '../types';

// Configure axios defaults
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (username: string, password: string): Promise<{ token: string }> => {
    const response = await api.post('/auth/login/', { username, password });
    return response.data;
  },
  logout: () => {
    localStorage.removeItem('authToken');
  },
};

// Client API
export const clientApi = {
  list: async (): Promise<Client[]> => {
    const response: AxiosResponse<PaginatedResponse<Client>> = await api.get('/clients/');
    return response.data.results;
  },
  
  create: async (client: ClientCreate): Promise<Client> => {
    const response: AxiosResponse<Client> = await api.post('/clients/', client);
    return response.data;
  },
  
  get: async (id: number): Promise<Client> => {
    const response: AxiosResponse<Client> = await api.get(`/clients/${id}/`);
    return response.data;
  },
  
  update: async (id: number, client: Partial<ClientCreate>): Promise<Client> => {
    const response: AxiosResponse<Client> = await api.patch(`/clients/${id}/`, client);
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await api.delete(`/clients/${id}/`);
  },
};

// Invoice API
export const invoiceApi = {
  list: async (params?: any): Promise<PaginatedResponse<Invoice>> => {
    const response: AxiosResponse<PaginatedResponse<Invoice>> = await api.get('/invoices/', { params });
    return response.data;
  },
  
  create: async (invoice: InvoiceCreate): Promise<Invoice> => {
    const response: AxiosResponse<Invoice> = await api.post('/invoices/', invoice);
    return response.data;
  },
  
  get: async (id: number): Promise<Invoice> => {
    const response: AxiosResponse<Invoice> = await api.get(`/invoices/${id}/`);
    return response.data;
  },
  
  update: async (id: number, invoice: Partial<InvoiceCreate>): Promise<Invoice> => {
    const response: AxiosResponse<Invoice> = await api.patch(`/invoices/${id}/`, invoice);
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await api.delete(`/invoices/${id}/`);
  },
  
  saveAsDraft: async (id: number): Promise<ApiResponse<Invoice>> => {
    const response: AxiosResponse<ApiResponse<Invoice>> = await api.post(`/invoices/${id}/save_as_draft/`);
    return response.data;
  },
  
  finalize: async (id: number): Promise<ApiResponse<Invoice>> => {
    const response: AxiosResponse<ApiResponse<Invoice>> = await api.post(`/invoices/${id}/finalize/`);
    return response.data;
  },
  
  copy: async (id: number): Promise<ApiResponse<Invoice>> => {
    const response: AxiosResponse<ApiResponse<Invoice>> = await api.post(`/invoices/${id}/copy/`);
    return response.data;
  },
  
  generateShareLink: async (id: number): Promise<ApiResponse<Invoice>> => {
    const response: AxiosResponse<ApiResponse<Invoice>> = await api.post(`/invoices/${id}/generate_share_link/`);
    return response.data;
  },
  
  revokeShareLink: async (id: number): Promise<ApiResponse<Invoice>> => {
    const response: AxiosResponse<ApiResponse<Invoice>> = await api.post(`/invoices/${id}/revoke_share_link/`);
    return response.data;
  },
  
  downloadPdf: async (id: number): Promise<Blob> => {
    const response: AxiosResponse<Blob> = await api.get(`/invoices/${id}/download_pdf/`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

// Public (share link) API
// Uses a separate axios instance on purpose: no auth token is attached and the
// 401 -> /login redirect interceptor does not apply to anonymous viewers.
const publicApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const publicInvoiceApi = {
  get: async (shareId: string): Promise<PublicInvoice> => {
    const response: AxiosResponse<PublicInvoice> = await publicApi.get(
      `/public/invoices/${encodeURIComponent(shareId)}/`
    );
    return response.data;
  },
  
  pdfUrl: (shareId: string): string => {
    return `${API_BASE_URL}/public/invoices/${encodeURIComponent(shareId)}/pdf/`;
  },
  
  downloadPdf: async (shareId: string): Promise<Blob> => {
    const response: AxiosResponse<Blob> = await publicApi.get(
      `/public/invoices/${encodeURIComponent(shareId)}/pdf/`,
      { responseType: 'blob' }
    );
    return response.data;
  },
};

// Invoice Item API
export const invoiceItemApi = {
  list: async (invoiceId?: number): Promise<InvoiceItem[]> => {
    const params = invoiceId ? { invoice: invoiceId } : {};
    const response: AxiosResponse<PaginatedResponse<InvoiceItem>> = await api.get('/invoice-items/', { params });
    return response.data.results;
  },
  
  create: async (item: InvoiceItemCreate): Promise<InvoiceItem> => {
    const response: AxiosResponse<InvoiceItem> = await api.post('/invoice-items/', item);
    return response.data;
  },
  
  get: async (id: number): Promise<InvoiceItem> => {
    const response: AxiosResponse<InvoiceItem> = await api.get(`/invoice-items/${id}/`);
    return response.data;
  },
  
  update: async (id: number, item: Partial<InvoiceItemCreate>): Promise<InvoiceItem> => {
    const response: AxiosResponse<InvoiceItem> = await api.patch(`/invoice-items/${id}/`, item);
    return response.data;
  },
  
  delete: async (id: number): Promise<void> => {
    await api.delete(`/invoice-items/${id}/`);
  },
  
  restore: async (id: number): Promise<ApiResponse<InvoiceItem>> => {
    const response: AxiosResponse<ApiResponse<InvoiceItem>> = await api.post(`/invoice-items/${id}/restore/`);
    return response.data;
  },
};

export default api;