"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { createDemoAccountService } from "@/lib/account/demo";
import type { Account, AccountService } from "@/lib/account/types";
import { isDesktopEdition } from "@/lib/edition";

type Status = "loading" | "signed-out" | "signed-in";

type AccountState = {
  status: Status;
  account: Account | null;
  /** True when this copy may open the studio. */
  owned: boolean;
  demo: boolean;
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  purchase: (planId: string) => Promise<void>;
};

const AccountContext = createContext<AccountState | null>(null);

/** Holds the current account for the whole page. */
export function AccountProvider({
  children,
  service: given,
}: {
  children: ReactNode;
  service?: AccountService;
}) {
  const service = useMemo(() => given ?? createDemoAccountService(), [given]);
  const [status, setStatus] = useState<Status>("loading");
  const [account, setAccount] = useState<Account | null>(null);

  useEffect(() => {
    let current = true;
    service
      .current()
      .then((found) => {
        if (!current) return;
        setAccount(found);
        setStatus(found ? "signed-in" : "signed-out");
      })
      .catch(() => {
        if (current) setStatus("signed-out");
      });
    return () => {
      current = false;
    };
  }, [service]);

  const state = useMemo<AccountState>(() => {
    const signedIn = (next: Account) => {
      setAccount(next);
      setStatus("signed-in");
    };
    return {
      status,
      account,
      owned: isDesktopEdition || account?.owned === true,
      demo: service.demo,
      signUp: async (email, password) => signedIn(await service.signUp(email, password)),
      signIn: async (email, password) => signedIn(await service.signIn(email, password)),
      signOut: async () => {
        await service.signOut();
        setAccount(null);
        setStatus("signed-out");
      },
      purchase: async (planId) => signedIn(await service.purchase(planId)),
    };
  }, [service, status, account]);

  return <AccountContext.Provider value={state}>{children}</AccountContext.Provider>;
}

export function useAccount(): AccountState {
  const state = useContext(AccountContext);
  if (!state) throw new Error("useAccount must be used inside <AccountProvider>.");
  return state;
}
