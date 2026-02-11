import { NuqsAdapter } from "nuqs/adapters/react-router/v6";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import {
  ConvexProvider,
  ConvexReactClient,
} from "convex/react";
import { Navbar } from "@/components/Navbar";
import Play from "@/pages/Play";
import Browse from "@/pages/Browse";
import Daily from "@/pages/Daily";

const convex = new ConvexReactClient(import.meta.env.VITE_CONVEX_URL as string);

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary font-sans antialiased flex flex-col">
      <Navbar />
      <main className="flex-1 flex flex-col">
        <Routes>
          <Route path="/" element={<Play />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/daily" element={<Daily />} />
        </Routes>
      </main>
    </div>
  );
}

export default function WrappedApp() {
  return (
    <NuqsAdapter>
      <BrowserRouter>
        <ConvexProvider client={convex}>
          <App />
        </ConvexProvider>
      </BrowserRouter>
    </NuqsAdapter>
  );
}
