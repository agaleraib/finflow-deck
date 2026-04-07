import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { PipelinePage } from "./pages/PipelinePage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/pipeline/:slug" element={<PipelinePage />} />
        <Route path="/reports" element={<PlaceholderPage title="Reports" />} />
        <Route path="/glossary" element={<PlaceholderPage title="Glossary Manager" />} />
      </Route>
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h2 className="font-serif text-2xl text-text-secondary">{title}</h2>
        <p className="text-text-muted text-sm mt-2">Coming in Phase 2</p>
      </div>
    </div>
  );
}
