/** A signed-in customer. ``owned`` is true once they have bought access. */
export type Account = {
  email: string;
  owned: boolean;
};

/**
 * Where accounts and purchases come from. The UI talks only to this, so the
 * demo stub can be replaced by Supabase Auth plus Stripe Checkout without
 * touching any component.
 */
export interface AccountService {
  /** True when nothing is really created or charged. The UI says so. */
  readonly demo: boolean;
  current(): Promise<Account | null>;
  signUp(email: string, password: string): Promise<Account>;
  signIn(email: string, password: string): Promise<Account>;
  signOut(): Promise<void>;
  /** Buy ``planId``. A real service redirects to checkout and never resolves. */
  purchase(planId: string): Promise<Account>;
}

export const MIN_PASSWORD_LENGTH = 8;

/** Why these credentials cannot be used, or ``null`` when they look fine. */
export function credentialProblem(email: string, password: string): string | null {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) return "Enter a valid email address.";
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Use a password of at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  return null;
}
