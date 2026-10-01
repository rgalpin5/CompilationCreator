"use client";

import Link from "next/link";
import { LockIcon } from "@/components/icons";
import SiteHeader from "@/components/SiteHeader";
import { buttonVariants } from "@/components/ui/button";
import { useAccount } from "@/features/account/AccountContext";
import PasswordGate from "@/features/auth/PasswordGate";
import { cn } from "@/lib/utils";
import Studio from "./Studio";

/**
 * Show the studio only to an account that has bought it. A hosted server's
 * own password check (PasswordGate) still applies after that.
 */
export default function StudioGate() {
  const { status, owned, account } = useAccount();

  if (owned) {
    return (
      <PasswordGate>
        <Studio />
      </PasswordGate>
    );
  }
  if (status === "loading") return null;

  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />
      <main className="bg-frame-grid flex flex-1 items-center justify-center p-4">
        <div className="flex w-full max-w-md flex-col items-center gap-4 rounded-xl bg-card p-8 text-center ring-1 ring-border">
          <span className="flex size-12 items-center justify-center rounded-full bg-primary/15 text-primary">
            <LockIcon className="size-5" />
          </span>
          <h1 className="font-heading text-2xl font-bold tracking-tight">The studio is locked</h1>
          <p className="text-sm text-muted-foreground">
            {account
              ? `${account.email} has no purchase yet. Buy lifetime access to open the studio.`
              : "Sign in with the account you bought CompCreator on, or get access first."}
          </p>
          <Link href="/#get-access" className={cn(buttonVariants({ size: "lg" }), "h-10 px-5")}>
            {account ? "Buy access" : "Sign in or buy"}
          </Link>
        </div>
      </main>
    </div>
  );
}
