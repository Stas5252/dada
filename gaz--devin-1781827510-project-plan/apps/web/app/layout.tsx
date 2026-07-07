import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { ChatWidgetGate } from "./components/ChatWidgetGate";
// import "./globals.css";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  display: "swap",
  variable: "--font-inter",
});

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
  openGraph: {
    title: "CallForce — AI-агенты для звонков и чатов",
    description: "Платформа AI-агентов нового поколения. Автоматизация входящих и исходящих звонков, чатов, поддержки и продаж.",
    url: "https://callforce.ru",
    siteName: "CallForce",
    images: [
      {
        url: "https://callforce.ru/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "CallForce Platform Preview",
      },
    ],
    locale: "ru_RU",
    type: "website",
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`dark scroll-smooth ${inter.variable}`}>
      <head>
        <link rel="stylesheet" href="/tailwind.css" />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased relative overflow-x-hidden">
        {children}
        <ChatWidgetGate />
        <Toaster theme="dark" position="bottom-right" richColors />
      </body>
    </html>
  );
}
