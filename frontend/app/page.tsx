import { AccountProvider } from "@/features/account/AccountContext";
import Landing from "@/features/landing/Landing";
import StudioGate from "@/features/studio/StudioGate";
import { isDesktopEdition } from "@/lib/edition";

export default function Home() {
  return (
    <AccountProvider>{isDesktopEdition ? <StudioGate /> : <Landing />}</AccountProvider>
  );
}
