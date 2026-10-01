import Link from "next/link";
import type { ReactNode } from "react";
import { LogoMark } from "@/components/icons";

/** The top bar shared by the landing page and the studio. */
export default function SiteHeader({ nav, actions }: { nav?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center gap-4 px-4 md:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2 rounded-md">
          <LogoMark className="size-7" />
          <span className="font-heading text-lg font-semibold tracking-tight">CompCreator</span>
        </Link>
        {nav && <nav className="flex min-w-0 items-center gap-1">{nav}</nav>}
        <div className="ml-auto flex shrink-0 items-center gap-2">{actions}</div>
      </div>
    </header>
  );
}
