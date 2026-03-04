import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { HomePage } from "@/pages/HomePage";

export function App(): React.JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        {/* Auth route placeholder — activate in v2 */}
        {/* <Route path="/login" element={<LoginPage />} /> */}
        {/* Redirect all unknown routes to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
