import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sorter Simulator",
  description: "Live HMI for the sorting machine simulator",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
