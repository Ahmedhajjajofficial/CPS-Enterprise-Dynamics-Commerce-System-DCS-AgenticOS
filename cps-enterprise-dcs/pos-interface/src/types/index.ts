/**
 * RockDeals POS - Type Definitions
 * ==================================
 * Core types for the POS interface.
 */

// Product Types
export interface Product {
  id: string;
  sku: string;
  name: string;
  description?: string;
  price: number;
  cost?: number;
  category: string;
  barcode?: string;
  taxRate: number;
  isActive: boolean;
  stockQuantity: number;
  imageUrl?: string;
}

// Cart Types
export interface CartItem {
  product: Product;
  quantity: number;
  discount: number;
  notes?: string;
}

export interface Cart {
  items: CartItem[];
  customer?: Customer;
  discount: number;
  taxAmount: number;
  subtotal: number;
  total: number;
}

// Customer Types
export interface Customer {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  loyaltyPoints: number;
  membershipTier: 'bronze' | 'silver' | 'gold' | 'platinum';
}

// Payment Types
export type PaymentMethod = 'cash' | 'card' | 'mobile' | 'loyalty' | 'split';

export interface Payment {
  method: PaymentMethod;
  amount: number;
  reference?: string;
  status: 'pending' | 'completed' | 'failed' | 'refunded';
}

// Transaction Types
export interface Transaction {
  id: string;
  sessionId: string;
  cashierId: string;
  branchId: string;
  cart: Cart;
  payments: Payment[];
  status: 'pending' | 'completed' | 'cancelled' | 'refunded';
  createdAt: string;
  completedAt?: string;
  receiptNumber: string;
}

// Session Types
export interface Session {
  id: string;
  cashierId: string;
  cashierName: string;
  registerId: string;
  branchId: string;
  openingBalance: number;
  closingBalance?: number;
  startedAt: string;
  endedAt?: string;
  status: 'active' | 'closed';
  transactionCount: number;
  totalSales: number;
}

// User Types
export interface User {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'manager' | 'cashier';
  permissions: string[];
  isActive: boolean;
}

// Sync Types
export interface SyncStatus {
  isOnline: boolean;
  lastSyncAt?: string;
  pendingTransactions: number;
  syncError?: string;
}

// UI Types
export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  duration?: number;
}

// API Types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Event Types
export interface PosEvent {
  type: 'SALE_COMPLETED' | 'SALE_CANCELLED' | 'INVENTORY_UPDATED' | 'SESSION_CLOSED';
  payload: unknown;
  timestamp: string;
}
