import type { Metadata } from "next";
import { AccountProvider } from "@/features/account/AccountContext";
import StudioGate from "@/features/studio/StudioGate";

export const metadata: Metadata = { title: "Studio · CompCreator" };

export default function StudioPage() {
  return (
    <AccountProvider>
      <StudioGate />
    </AccountProvider>
  );
}
