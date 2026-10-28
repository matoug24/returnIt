import type { Metadata } from "next";
import "./styles.css";
import "./workflow.css";
import {Nav,SessionProvider} from "@/components/session";

export const metadata: Metadata = {
  title: "Returnet — Montreal return pickup",
  description: "Bilingual pickup and evidenced delivery for prepared online returns."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <SessionProvider><Nav/>{children}</SessionProvider>
      </body>
    </html>
  );
}
