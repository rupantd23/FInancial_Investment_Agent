import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FINN — Investor intelligence",
  description: "A source-backed daily workspace for public-markets investors.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
