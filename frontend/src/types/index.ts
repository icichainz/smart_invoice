// User types
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

// Business profile (sender details printed on invoices)
export interface BusinessProfile {
  business_name: string;
  address: string;
  email: string;
  phone: string;
  tax_id: string;
  payment_instructions: string;
  footer_note: string;
}

// Client types
export interface Client {
  id: number;
  name: string;
  email: string;
  phone: string;
}

export interface ClientCreate {
  name: string;
  email: string;
  phone: string;
}

// Invoice Item types
export interface InvoiceItem {
  id: number;
  title: string;
  description: string;
  amount: string;
  quantity: number;
  total_amount: string;
  is_active: boolean;
}

export interface InvoiceItemCreate {
  invoice: number;
  title: string;
  description: string;
  amount: string;
  quantity: number;
}

// Invoice types
export interface Invoice {
  id: number;
  number: string;
  client: number;
  client_name: string;
  user: number;
  user_name: string;
  created_at: string;
  due_date: string | null;
  vat_rate: number;
  total_amount: string;
  total_amount_final: string;
  vat_rate_amount: string;
  status: 'paid' | 'unpaid';
  save_as_draft: boolean;
  is_closed: boolean;
  share_link_id: string | null;
  sent: 'sent' | 'not sent';
  sent_at: string | null;
  items: InvoiceItem[];
}

export interface InvoiceCreate {
  client?: number;
  due_date?: string;
  vat_rate?: number;
  status?: 'paid' | 'unpaid';
  save_as_draft?: boolean;
  sent?: 'sent' | 'not sent';
  items?: InvoiceItemCreate[];
}

// Public (share link) invoice types
export interface PublicInvoiceItem {
  title: string | null;
  description: string | null;
  amount: string;
  quantity: number;
  total_amount: string;
}

export interface PublicInvoice {
  id: number;
  number: string;
  created_at: string;
  due_date: string | null;
  status: 'paid' | 'unpaid';
  vat_rate: number;
  total_amount: string;
  vat_rate_amount: string;
  total_amount_final: string;
  client_name: string | null;
  client_email: string | null;
  items: PublicInvoiceItem[];
}

// API Response types
export interface ApiResponse<T> {
  status: 'success' | 'error';
  message: string;
  data?: T;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Form types
export interface InvoiceFormData {
  client: Client | null;
  due_date: string;
  vat_rate: number;
  status: 'paid' | 'unpaid';
  items: InvoiceItemCreate[];
}

// Navigation types
export interface NavItem {
  label: string;
  path: string;
  icon?: string;
}