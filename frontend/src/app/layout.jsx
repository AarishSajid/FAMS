import "./globals.css";
import "ol/ol.css";
import { FamsProvider } from "@/lib/store";

export const metadata = {
  title: "FAMS — Farmer Advisory Management System",
  description: "Human-in-the-loop advisory control for the Agriverse ecosystem",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body>
        <FamsProvider>{children}</FamsProvider>
      </body>
    </html>
  );
}
