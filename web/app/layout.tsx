import type { Metadata } from "next";
import { Caveat, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { MARCA, SLOGAN_TITULO } from "@/lib/marca";

const jakarta = Plus_Jakarta_Sans({
  variable: "--font-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});
const caveat = Caveat({ variable: "--font-caveat", subsets: ["latin"], weight: ["500", "600"] });

export const metadata: Metadata = {
  title: `${MARCA} — ${SLOGAN_TITULO}`,
  description: "Descubra quanto proteger e compare seguros de vida pela aderência à sua necessidade.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${jakarta.variable} ${caveat.variable}`}>
      <body className="min-h-screen flex flex-col">{children}</body>
    </html>
  );
}
