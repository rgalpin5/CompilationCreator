"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TooManyAttemptsError, UnauthorizedError, rememberPassword } from "@/lib/api/auth";
import { checkSession } from "@/lib/api/session";

type State = "checking" | "open" | "locked";

/**
 * Ask for the server's password before showing the app.
 *
 * Local and desktop servers set no password, so the check passes at once. Any
 * failure other than a 401 or 429 opens the app too, where the usual error
 * messages explain an unreachable API.
 */
export default function PasswordGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>("checking");
  const [password, setPassword] = useState("");
  // Why the last attempt failed, shown under the field.
  const [problem, setProblem] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let current = true;
    checkSession()
      .then(() => {
        if (current) setState("open");
      })
      .catch((caught: unknown) => {
        if (!current) return;
        if (caught instanceof TooManyAttemptsError) setProblem(caught.message);
        const locked = caught instanceof UnauthorizedError || caught instanceof TooManyAttemptsError;
        setState(locked ? "locked" : "open");
      });
    return () => {
      current = false;
    };
  }, []);

  async function unlock(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const value = password.trim();
    if (submitting || !value) return;
    setSubmitting(true);
    // Requests read the password from storage, so store it before checking.
    rememberPassword(value);
    try {
      await checkSession();
      setState("open");
    } catch (caught: unknown) {
      if (caught instanceof UnauthorizedError) {
        rememberPassword("");
        setProblem("That password is wrong.");
      } else if (caught instanceof TooManyAttemptsError) {
        rememberPassword("");
        setProblem(caught.message);
      } else {
        setState("open");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (state === "open") return children;
  if (state === "checking") return null;
  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center p-4">
      <Card className="shadow-sm">
        <CardHeader className="border-b">
          <CardTitle>CompCreator</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3" onSubmit={unlock}>
            <label className="flex flex-col gap-1 text-sm">
              Server password
              <Input
                type="password"
                autoComplete="current-password"
                value={password}
                disabled={submitting}
                aria-invalid={problem ? true : undefined}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setProblem(null);
                }}
              />
            </label>
            {problem && <p className="text-sm text-destructive">{problem}</p>}
            <p className="text-sm text-muted-foreground">
              This browser remembers the password once it works.
            </p>
            <Button type="submit" disabled={submitting || !password.trim()}>
              {submitting ? "Checking…" : "Continue"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
