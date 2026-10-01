"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MIN_PASSWORD_LENGTH } from "@/lib/account/types";
import { errorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { useAccount } from "./AccountContext";

type Mode = "sign-up" | "sign-in";

/** Create an account or sign in; once signed in, show who and offer sign-out. */
export default function AccountPanel() {
  const { status, account, signUp, signIn, signOut } = useAccount();
  const [mode, setMode] = useState<Mode>("sign-up");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setProblem(null);
    try {
      await (mode === "sign-up" ? signUp : signIn)(email, password);
      setPassword("");
    } catch (caught: unknown) {
      setProblem(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "loading") return <div className="min-h-72" />;

  if (account) {
    return (
      <div className="flex min-h-72 flex-col justify-between gap-6">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
            Signed in
          </p>
          <p className="truncate font-heading text-xl font-semibold">{account.email}</p>
          <p className="text-sm text-muted-foreground">
            {account.owned ? "Lifetime access is active." : "No purchase on this account yet."}
          </p>
        </div>
        <Button type="button" variant="outline" className="self-start" onClick={() => void signOut()}>
          Sign out
        </Button>
      </div>
    );
  }

  return (
    <div className="flex min-h-72 flex-col gap-5">
      <div role="tablist" aria-label="Account" className="inline-flex self-start rounded-lg bg-muted p-1">
        {(["sign-up", "sign-in"] as const).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={mode === value}
            onClick={() => {
              setMode(value);
              setProblem(null);
            }}
            className={cn(
              "rounded-md px-3 py-1 text-sm transition-colors",
              mode === value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {value === "sign-up" ? "Create account" : "Sign in"}
          </button>
        ))}
      </div>
      <form className="flex flex-col gap-3" onSubmit={submit} noValidate>
        <label className="flex flex-col gap-1.5 text-sm">
          Email
          <Input
            type="email"
            autoComplete="email"
            value={email}
            disabled={submitting}
            onChange={(event) => setEmail(event.target.value)}
            className="h-10"
          />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          Password
          <Input
            type="password"
            autoComplete={mode === "sign-up" ? "new-password" : "current-password"}
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            disabled={submitting}
            aria-invalid={problem ? true : undefined}
            onChange={(event) => setPassword(event.target.value)}
            className="h-10"
          />
        </label>
        {problem && <p className="text-sm text-destructive">{problem}</p>}
        <Button type="submit" size="lg" className="mt-1 h-10" disabled={submitting || !email || !password}>
          {submitting ? "One moment…" : mode === "sign-up" ? "Create account" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
