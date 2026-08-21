/**
 * Screen switching is one `useState`. Six screens with a single linear flow do
 * not justify a router dependency, URL parsing, or a state library.
 */

import { useState } from 'react';
import AppShell from './components/AppShell';
import DashboardPage from './pages/DashboardPage';
import ExportPage from './pages/ExportPage';
import ProcessingPage from './pages/ProcessingPage';
import ProductDetailPage from './pages/ProductDetailPage';
import ReviewPage from './pages/ReviewPage';
import UploadPage from './pages/UploadPage';

export type Screen = 'upload' | 'processing' | 'dashboard' | 'detail' | 'review' | 'export';

export default function App() {
  const [screen, setScreen] = useState<Screen>('upload');
  const [jobId, setJobId] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [rowId, setRowId] = useState<number | null>(null);

  function startJob(id: string, name: string) {
    setJobId(id);
    setFilename(name);
    setRowId(null);
    setScreen('processing');
  }

  function openRow(id: number) {
    setRowId(id);
    setScreen('detail');
  }

  return (
    <AppShell
      screen={screen}
      onNavigate={setScreen}
      jobId={jobId}
      jobLabel={filename ?? undefined}
    >
      {screen === 'upload' && <UploadPage onStart={startJob} />}

      {screen === 'processing' && jobId && (
        <ProcessingPage jobId={jobId} onComplete={() => setScreen('dashboard')} />
      )}

      {screen === 'dashboard' && jobId && (
        <DashboardPage jobId={jobId} onOpenRow={openRow} onNavigate={setScreen} />
      )}

      {screen === 'detail' && jobId && rowId !== null && (
        <ProductDetailPage jobId={jobId} rowId={rowId} onBack={() => setScreen('dashboard')} />
      )}

      {screen === 'review' && jobId && <ReviewPage jobId={jobId} onOpenRow={openRow} />}

      {screen === 'export' && jobId && <ExportPage jobId={jobId} />}

      {/* Guard: a job-scoped screen reached before a job exists. */}
      {screen !== 'upload' && !jobId && (
        <div className="border border-ink-graphite bg-surface-bright p-8 max-w-xl">
          <div className="font-label-caps text-label-caps text-secondary uppercase mb-2">
            No active job
          </div>
          <p className="font-body-md text-body-md text-ink-graphite">
            Ingest a supplier file before opening this view.
          </p>
        </div>
      )}
    </AppShell>
  );
}
