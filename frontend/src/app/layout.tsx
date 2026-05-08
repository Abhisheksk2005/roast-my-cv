import type { Metadata } from "next";
import "./globals.css";
import { FirebaseRoot } from "@/components/FirebaseRoot";

export const metadata: Metadata = {
  title: "Donald | Is AI Coming For Your Job?",
  description:
    "An AI that tells you how replaceable your job is, whether your degree still holds value, and gives you a clear path to stay ahead. No sugarcoating.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <FirebaseRoot />
        {children}
      </body>
    </html>
  );
}
