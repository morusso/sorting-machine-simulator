import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Orders",
  description: "Order/package storage service admin UI",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
