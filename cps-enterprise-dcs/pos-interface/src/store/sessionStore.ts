/**
 * Session Store - Zustand
 * =======================
 * Manages the cashier session state.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Session, User, SyncStatus } from '../types';

interface SessionState {
  // Current session
  currentSession: Session | null;
  currentUser: User | null;
  
  // Sync status
  syncStatus: SyncStatus;
  
  // Actions
  login: (user: User) => void;
  logout: () => void;
  startSession: (openingBalance: number, registerId: string) => void;
  endSession: (closingBalance: number) => void;
  updateSyncStatus: (status: Partial<SyncStatus>) => void;
  incrementTransactionCount: (amount: number) => void;
}

const initialSyncStatus: SyncStatus = {
  isOnline: true,
  pendingTransactions: 0
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      currentSession: null,
      currentUser: null,
      syncStatus: initialSyncStatus,

      login: (user) => {
        set({ currentUser: user });
      },

      logout: () => {
        set({ 
          currentUser: null,
          currentSession: null 
        });
      },

      startSession: (openingBalance, registerId) => {
        const { currentUser } = get();
        if (!currentUser) return;

        const newSession: Session = {
          id: `session-${Date.now()}`,
          cashierId: currentUser.id,
          cashierName: currentUser.name,
          registerId,
          branchId: 'BR001', // TODO: Get from config
          openingBalance,
          startedAt: new Date().toISOString(),
          status: 'active',
          transactionCount: 0,
          totalSales: 0
        };

        set({ currentSession: newSession });
      },

      endSession: (closingBalance) => {
        const { currentSession } = get();
        if (!currentSession) return;

        set({
          currentSession: {
            ...currentSession,
            closingBalance,
            endedAt: new Date().toISOString(),
            status: 'closed'
          }
        });
      },

      updateSyncStatus: (status) => {
        const { syncStatus } = get();
        set({
          syncStatus: { ...syncStatus, ...status }
        });
      },

      incrementTransactionCount: (amount) => {
        const { currentSession } = get();
        if (!currentSession) return;

        set({
          currentSession: {
            ...currentSession,
            transactionCount: currentSession.transactionCount + 1,
            totalSales: currentSession.totalSales + amount
          }
        });
      }
    }),
    {
      name: 'pos-session-storage',
      partialize: (state) => ({ 
        currentUser: state.currentUser,
        currentSession: state.currentSession 
      })
    }
  )
);
