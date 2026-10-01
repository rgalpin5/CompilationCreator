import { describe, expect, it } from "vitest";
import { createDemoAccountService } from "./demo";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => void values.set(key, value),
  };
}

describe("demo account service", () => {
  it("starts signed out", async () => {
    expect(await createDemoAccountService(memoryStorage()).current()).toBeNull();
  });

  it("signs up without storing the password", async () => {
    const storage = memoryStorage();
    const service = createDemoAccountService(storage);
    const account = await service.signUp(" Me@Example.com ", "correct horse");
    expect(account).toEqual({ email: "me@example.com", owned: false });
    expect([...storage.values.values()].join()).not.toContain("correct horse");
  });

  it("rejects a bad email or short password", async () => {
    const service = createDemoAccountService(memoryStorage());
    await expect(service.signUp("nope", "long enough")).rejects.toThrow("valid email");
    await expect(service.signUp("me@example.com", "short")).rejects.toThrow("at least 8");
  });

  it("refuses a purchase while signed out", async () => {
    const service = createDemoAccountService(memoryStorage());
    await expect(service.purchase("lifetime")).rejects.toThrow("sign in first");
  });

  it("keeps a purchase across sign-out for the same email only", async () => {
    const service = createDemoAccountService(memoryStorage());
    await service.signUp("me@example.com", "password1");
    expect(await service.purchase("lifetime")).toEqual({ email: "me@example.com", owned: true });
    await service.signOut();
    expect(await service.current()).toBeNull();
    expect((await service.signIn("me@example.com", "password1")).owned).toBe(true);
    await service.signOut();
    expect((await service.signIn("other@example.com", "password1")).owned).toBe(false);
  });

  it("ignores unreadable stored data", async () => {
    const storage = memoryStorage();
    storage.setItem("compcreator.demoAccount", "{not json");
    expect(await createDemoAccountService(storage).current()).toBeNull();
  });
});
