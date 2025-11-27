import type { Metadata } from "next";
import { Inter, Geist_Mono, Playfair_Display } from "next/font/google";
import ClerkWrapper from "@/components/ClerkWrapper";
import { UserProvider } from "@/context/UserContext";
import "./globals.css";
import TopbarWrapper from "@/components/TopbarWrapper";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
});

const playfair = Playfair_Display({
  variable: "--font-serif",
  subsets: ["latin"],
  display: "swap",
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
        className={`${inter.variable} ${playfair.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning={true}
      >
        <ClerkWrapper>
          {/* UserProvider handles both context AND detailed sync logging */}
          <UserProvider>
            <TopbarWrapper />
            {children}
          </UserProvider>
        </ClerkWrapper>
      </body>
    </html>
  );
}
