import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { StartPage } from '@/pages/StartPage';
import { ConsultationPage } from '@/pages/ConsultationPage';
import { ReviewPage } from '@/pages/ReviewPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<StartPage />} />
        <Route path="/encounter/:id" element={<ConsultationPage />} />
        <Route path="/encounter/:id/review" element={<ReviewPage />} />
      </Routes>
    </BrowserRouter>
  );
}
