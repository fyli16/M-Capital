import type { Metadata } from "next";
import "@/app/globals.css";

import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Aegis Capital — AI Investment Research",
  description: "Multi-agent AI investment research firm.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
