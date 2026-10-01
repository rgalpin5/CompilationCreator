import { readStored, writeStored } from "@/lib/storage";
import { credentialProblem, type Account, type AccountService } from "./types";

const KEY = "compcreator.demoAccount";

type StringStorage = Pick<Storage, "getItem" | "setItem">;

/** What the demo keeps in this browser. Never the password. */
type Record = Account & { signedIn: boolean };

function parse(raw: string | null): Record | null {
  if (!raw) return null;
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null) return null;
    const { email, owned, signedIn } = value as { [key: string]: unknown };
    if (typeof email !== "string" || typeof owned !== "boolean" || typeof signedIn !== "boolean") {
      return null;
    }
    return { email, owned, signedIn };
  } catch {
    return null;
  }
}

/**
 * A stand-in account service that keeps one account in this browser. It never
 * stores the password and takes no payment: "buying" only marks the account as
 * owned. Replace it with the real provider before charging anyone.
 */
export function createDemoAccountService(storage?: StringStorage): AccountService {
  const load = () => parse(readStored(KEY, storage));
  const save = (record: Record) => writeStored(KEY, JSON.stringify(record), storage);
  const account = ({ email, owned }: Record): Account => ({ email, owned });

  function address(email: string, password: string): string {
    const problem = credentialProblem(email, password);
    if (problem) throw new Error(problem);
    return email.trim().toLowerCase();
  }

  return {
    demo: true,
    async current() {
      const record = load();
      return record?.signedIn ? account(record) : null;
    },
    async signUp(email, password) {
      const record = { email: address(email, password), owned: false, signedIn: true };
      save(record);
      return account(record);
    },
    async signIn(email, password) {
      const wanted = address(email, password);
      const known = load();
      // No server to check against: any sign-in works, and a returning email keeps its purchase.
      const record = { email: wanted, owned: known?.email === wanted && known.owned, signedIn: true };
      save(record);
      return account(record);
    },
    async signOut() {
      const known = load();
      if (known) save({ ...known, signedIn: false });
    },
    async purchase() {
      const known = load();
      if (!known?.signedIn) throw new Error("Create an account or sign in first.");
      const record = { ...known, owned: true };
      save(record);
      return account(record);
    },
  };
}
