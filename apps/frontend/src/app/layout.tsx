import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'NASCAR DFS Engine',
  description: 'Axiomatic NASCAR DraftKings DFS optimization engine',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <div className="min-h-screen bg-gray-50">
          <header className="bg-blue-600 text-white py-4 shadow-md">
            <div className="container mx-auto px-4">
              <h1 className="text-2xl font-bold">NASCAR DFS Engine</h1>
              <p className="text-sm text-blue-100">Axiomatic DraftKings Optimization</p>
            </div>
          </header>
          <main className="container mx-auto px-4 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
