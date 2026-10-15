import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TradeGear — Trading Dashboard",
  description:
    "No-Code TradingView Automator & Risk Management Dashboard for Forex/Gold MT5 traders",
};

import { AuthProvider } from "@/context/AuthContext";
import { WebSocketProvider } from "@/context/WebSocketContext";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <WebSocketProvider>{children}</WebSocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
