import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import "./globals.css";
import SideBar from "./components/SideBar";
import Providers from "./providers";
import { getServerSession } from "next-auth";
import { authOptions } from "./lib/auth-options";

const roboto = Roboto({
  variable: "--font-roboto",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MedControl",
  description: "Tu asistente personal para la adherencia a tratamientos médicos",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getServerSession(authOptions);

  return (
    <html
      lang="es"
      className={`${roboto.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-row">
        <Providers>
          {session && <SideBar />}
          <div className="flex-1 bg-blue-100">{children}</div>
        </Providers>
      </body>
    </html>
  );
}
