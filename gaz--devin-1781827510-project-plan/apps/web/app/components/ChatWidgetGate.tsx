"use client";

import { usePathname } from "next/navigation";
import { ChatWidget } from "./ChatWidget";

const HIDDEN_PREFIXES = [
  "/agents",
  "/analytics",
  "/conversations",
  "/dashboard",
  "/forgot-password",
  "/knowledge",
  "/login",
  "/onboarding",
  "/register",
  "/reset-password",
  "/settings",
  "/test-console",
  "/verify-email",
  "/widget",
];

export function ChatWidgetGate() {
  const pathname = usePathname();
  const shouldHide = HIDDEN_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));

  if (shouldHide) {
    return null;
  }

  return <ChatWidget />;
}
