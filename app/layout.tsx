import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oncogon AI | OSIEL Research Engine",
  description:
    "Research-use compound intelligence, transparent prioritization, and governed experimental learning.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
