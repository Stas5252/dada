import type { Metadata } from "next";
import "./globals.css";

import { ChatWidgetGate } from "./components/ChatWidgetGate";

export const metadata: Metadata = {
  title: "CallForce — AI-агенты для звонков и чатов",
  description:
    "Платформа AI-агентов нового поколения. Автоматизация входящих и исходящих звонков, чатов, поддержки и продаж. Лучше, чем Bland.ai — для рынка РФ и СНГ.",
  keywords: [
    "AI звонки",
    "голосовой агент",
    "автоматизация поддержки",
    "cold calling AI",
    "чат-бот",
    "CallForce",
  ],
};

import { Toaster } from "sonner";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="dark scroll-smooth">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
        <ChatWidgetGate />
        <Toaster theme="dark" position="bottom-right" richColors />
      </body>
    </html>
  );
}
