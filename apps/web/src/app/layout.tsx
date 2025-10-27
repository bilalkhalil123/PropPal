import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import ClerkWrapper from "@/components/ClerkWrapper";
import { UserProvider } from "@/context/UserContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PropPal - AI-Powered Real Estate Platform",
  description: "Multi-Agent AI-Powered Real Estate Platform for Pakistan",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning={true}
      >
        <ClerkWrapper>
          {/* UserProvider handles both context AND detailed sync logging */}
          <UserProvider>
            {children}
          </UserProvider>
        </ClerkWrapper>
      </body>
    </html>
  );
}
