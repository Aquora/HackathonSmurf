import { expect, test } from "@playwright/test";

test("header menu opens, closes, and works from the keyboard", async ({ page }) => {
  await page.goto("/");
  const button = page.getByRole("button", { name: "Menu" });
  const menu = page.getByRole("menu", { name: "Menu" });

  // Mouse: open, then close by clicking outside.
  await expect(button).toHaveAttribute("aria-expanded", "false");
  await button.click();
  await expect(menu).toBeVisible();
  await expect(menu.getByRole("menuitem")).toHaveText(["Player settings", "Support (coming soon)"]);
  await expect(menu.getByRole("menuitem", { name: /Support/ })).toHaveAttribute("aria-disabled", "true");
  await page.mouse.click(20, 400);
  await expect(menu).toBeHidden();

  // Keyboard: ArrowDown opens and focuses the first item, arrows move, Escape returns focus.
  await button.focus();
  await page.keyboard.press("ArrowDown");
  await expect(menu.getByRole("menuitem", { name: "Player settings" })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(menu.getByRole("menuitem", { name: /Support/ })).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(menu.getByRole("menuitem", { name: "Player settings" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menu).toBeHidden();
  await expect(button).toBeFocused();

  // Player settings goes to the (protected) settings page, and the menu closes.
  await button.click();
  await menu.getByRole("menuitem", { name: "Player settings" }).click();
  await expect(page).toHaveURL(/\/sign-in\?callbackUrl=.*settings/);
  await expect(menu).toBeHidden();
});
