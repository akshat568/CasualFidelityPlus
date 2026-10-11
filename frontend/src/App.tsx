import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppSidebar } from './components/common/AppSidebar';
import { AppHeader } from './components/common/AppHeader';
import { DashboardPage } from './pages/DashboardPage';
import { WorkbenchPage } from './pages/WorkbenchPage';
import { ResearchPage } from './pages/ResearchPage';
import { ExplorerPage } from './pages/ExplorerPage';
import { ReportsPage } from './pages/ReportsPage';
import { healthCheck, getApiBaseUrl, setApiBaseUrl } from './services/api';

export function App() {
  const [apiBaseUrl, setApiUrl] = useState<string>(getApiBaseUrl());
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  const verifyHealth = useCallback((urlToTest?: string) => {
    const targetUrl = urlToTest || apiBaseUrl;
    setConnectionStatus('checking');

    healthCheck(targetUrl)
      .then(() => {
        setConnectionStatus('connected');
      })
      .catch(() => {
        setConnectionStatus('disconnected');
      });
  }, [apiBaseUrl]);

  useEffect(() => {
    verifyHealth();
    const interval = setInterval(() => verifyHealth(), 15000);
    return () => clearInterval(interval);
  }, [verifyHealth]);

  const handleUpdateApiUrl = (newUrl: string) => {
    setApiBaseUrl(newUrl);
    setApiUrl(newUrl);
    verifyHealth(newUrl);
  };

  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-[#FDFBF7] text-[#1F2937]">
        {/* Left Sidebar */}
        <AppSidebar
          apiBaseUrl={apiBaseUrl}
          isApiConnected={connectionStatus === 'connected'}
          connectionStatus={connectionStatus}
          onUpdateApiUrl={handleUpdateApiUrl}
          onRefreshConnection={() => verifyHealth()}
        />

        {/* Main Layout Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <AppHeader
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />

          {/* Main Content View */}
          <main className="flex-1 p-6 overflow-y-auto">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/workbench" element={<WorkbenchPage />} />
              <Route path="/research" element={<ResearchPage />} />
              <Route path="/experiments" element={<ExplorerPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              {/* Redirect removed /settings route cleanly to avoid broken navigation */}
              <Route path="/settings" element={<Navigate to="/" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
