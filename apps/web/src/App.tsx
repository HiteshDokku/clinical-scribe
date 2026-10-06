import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { StartPage } from '@/pages/StartPage';
import { ConsultationPage } from '@/pages/ConsultationPage';
import { ReviewPage } from '@/pages/ReviewPage';
import { AuditDashboard } from '@/pages/AuditDashboard';
import { EncounterAuditDetail } from '@/pages/EncounterAuditDetail';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { RoleSwitcher } from '@/components/common/RoleSwitcher';

export default function App() {
  return (
    <BrowserRouter>
      <RoleSwitcher />
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<StartPage />} />
          <Route path="/encounter/:id" element={<ConsultationPage />} />
          <Route path="/encounter/:id/review" element={<ReviewPage />} />
          <Route path="/audit" element={<AuditDashboard />} />
          <Route path="/audit/:id" element={<EncounterAuditDetail />} />
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
