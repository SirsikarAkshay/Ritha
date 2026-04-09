// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import Layout from './components/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import WardrobePage from './pages/WardrobePage.jsx'
import ItineraryPage from './pages/ItineraryPage.jsx'
import TripPlannerPage from './pages/TripPlannerPage.jsx'
import CulturalPage from './pages/CulturalPage.jsx'
import SustainabilityPage from './pages/SustainabilityPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import VerifyEmailPage from './pages/VerifyEmailPage.jsx'
import CalendarPage from './pages/CalendarPage.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import ForgotPasswordPage from './pages/ForgotPasswordPage.jsx'
import ResetPasswordPage from './pages/ResetPasswordPage.jsx'
import { useToast } from './hooks/useToast.jsx'
import { ToastList } from './components/Toast.jsx'

function Spinner() {
  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--midnight)' }}>
      <div style={{ textAlign:'center' }}>
        <div style={{ fontFamily:'var(--font-display)', fontSize:'1.75rem', color:'var(--cream)', letterSpacing:'-0.02em', marginBottom:'20px' }}>
          Arokah
        </div>
        <div className="spinner" style={{ margin:'0 auto' }} />
      </div>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (!user)   return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/verify-email"     element={<VerifyEmailPage />} />
      <Route path="/forgot-password"  element={<ForgotPasswordPage />} />
      <Route path="/reset-password"   element={<ResetPasswordPage />} />

      <Route path="/" element={
        <ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>
      } />
      <Route path="/wardrobe" element={
        <ProtectedRoute><Layout><WardrobePage /></Layout></ProtectedRoute>
      } />
      <Route path="/itinerary" element={
        <ProtectedRoute><Layout><ItineraryPage /></Layout></ProtectedRoute>
      } />
      <Route path="/calendar" element={
        <ProtectedRoute><Layout><CalendarPage /></Layout></ProtectedRoute>
      } />
      <Route path="/trips" element={
        <ProtectedRoute><Layout><TripPlannerPage /></Layout></ProtectedRoute>
      } />
      <Route path="/cultural" element={
        <ProtectedRoute><Layout><CulturalPage /></Layout></ProtectedRoute>
      } />
      <Route path="/sustainability" element={
        <ProtectedRoute><Layout><SustainabilityPage /></Layout></ProtectedRoute>
      } />
      <Route path="/profile" element={
        <ProtectedRoute><Layout><ProfilePage /></Layout></ProtectedRoute>
      } />

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

function ToastRoot() {
  const { toasts, toast } = useToast()
  // Expose toast globally for easy use from any page
  if (typeof window !== 'undefined') window.__toast = toast
  return <ToastList toasts={toasts} />
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <ToastRoot />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  )
}
