import { Route, Routes } from "react-router-dom";

import CalculatorPage from "./pages/CalculatorPage";
import CritiquePage from "./pages/CritiquePage";
import RoadmapPage from "./pages/RoadmapPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  return (
    <div className="min-h-screen bg-background text-white">
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/critique" element={<CritiquePage />} />
        <Route path="/roadmap" element={<RoadmapPage />} />
        <Route path="/calculator" element={<CalculatorPage />} />
      </Routes>
    </div>
  );
}
