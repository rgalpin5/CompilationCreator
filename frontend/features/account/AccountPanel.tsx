"use client";

import { useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MIN_PASSWORD_LENGTH } from "@/lib/account/types";
import { errorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";
import { useAccount } from "./AccountContext";

type Mode = "sign-up" | "sign-in";

const MODES = ["sign-up", "sign-in"] as const;

/** Create an account or sign in; once signed in, show who and offer sign-out. */
export default function AccountPanel() {
  const { status, account, signUp, signIn, signOut } = useAccount();
  const [mode, setMode] = useState<Mode>("sign-up");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const id = useId();
  const tabRefs = useRef<Partial<Record<Mode, HTMLButtonElement | null>>>({});

  function choose(value: Mode) {
    setMode(value);
    setProblem(null);
  }

  // Tabs pattern: arrows, Home and End move between the two modes; Tab goes on to the form.
  function onTabKey(event: KeyboardEvent<HTMLButtonElement>) {
    const index = MODES.indexOf(mode);
    const next =
      event.key === "ArrowRight" ? MODES[(index + 1) % MODES.length]
      : event.key === "ArrowLeft" ? MODES[(index - 1 + MODES.length) % MODES.length]
      : event.key === "Home" ? MODES[0]
      : event.key === "End" ? MODES[MODES.length - 1]
      : undefined;
    if (!next) return;
    event.preventDefault();
    choose(next);
    tabRefs.current[next]?.focus();
  }

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
        {MODES.map((value) => (
          <button
            key={value}
            ref={(element) => {
              tabRefs.current[value] = element;
            }}
            id={`${id}-${value}`}
            type="button"
            role="tab"
            aria-selected={mode === value}
            aria-controls={`${id}-panel`}
            tabIndex={mode === value ? 0 : -1}
            onClick={() => choose(value)}
            onKeyDown={onTabKey}
            className={cn(
              "focus-ring rounded-sm px-3 py-1 text-sm transition-[color,background-color,box-shadow] duration-150",
              mode === value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {value === "sign-up" ? "Create account" : "Sign in"}
          </button>
        ))}
      </div>
      <form
        id={`${id}-panel`}
        role="tabpanel"
        aria-labelledby={`${id}-${mode}`}
        className="flex flex-col gap-3"
        onSubmit={submit}
        noValidate
      >
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
            aria-describedby={problem ? `${id}-problem` : undefined}
            onChange={(event) => setPassword(event.target.value)}
            className="h-10"
          />
        </label>
        {problem && (
          <p id={`${id}-problem`} role="alert" className="text-sm text-destructive">
            {problem}
          </p>
        )}
        <Button type="submit" size="lg" className="mt-1 h-10" disabled={submitting || !email || !password}>
          {submitting ? "One moment…" : mode === "sign-up" ? "Create account" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
