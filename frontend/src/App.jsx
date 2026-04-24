// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import { ThemeProvider } from './hooks/useTheme.jsx'
import Layout from './components/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ForgotPassword from './pages/ForgotPassword.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import VerifyEmail from './pages/VerifyEmail.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import WardrobePage from './pages/WardrobePage.jsx'
import ItineraryPage from './pages/ItineraryPage.jsx'
import TripPlannerPage from './pages/TripPlannerPage.jsx'
import CulturalPage from './pages/CulturalPage.jsx'
import SustainabilityPage from './pages/SustainabilityPage.jsx'
import PeoplePage from './pages/PeoplePage.jsx'
import MessagesPage from './pages/MessagesPage.jsx'
import SharedWardrobesPage from './pages/SharedWardrobesPage.jsx'
import SharedWardrobeDetailPage from './pages/SharedWardrobeDetailPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import OutfitHistoryPage from './pages/OutfitHistoryPage.jsx'

import { useToast } from './hooks/useToast.jsx'
import { ToastList } from './components/Toast.jsx'

const ForgotPasswordPage = ForgotPassword
const ResetPasswordPage = ResetPassword
const VerifyEmailPage = VerifyEmail

function Spinner() {
  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', background:'var(--midnight)' }}>
      <div style={{ textAlign:'center' }}>
        <div style={{ fontFamily:'var(--font-display)', fontSize:'1.75rem', color:'var(--cream)', letterSpacing:'-0.02em', marginBottom:'20px' }}>
          Ritha
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
      <Route path="/forgot-password" element={user ? <Navigate to="/" replace /> : <ForgotPasswordPage />} />
      <Route path="/reset-password" element={user ? <Navigate to="/" replace /> : <ResetPasswordPage />} />
      <Route path="/verify-email" element={user ? <Navigate to="/" replace /> : <VerifyEmailPage />} />

      <Route path="/" element={
        <ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>
      } />
      <Route path="/wardrobe" element={
        <ProtectedRoute><Layout><WardrobePage /></Layout></ProtectedRoute>
      } />
      <Route path="/itinerary" element={
        <ProtectedRoute><Layout><ItineraryPage /></Layout></ProtectedRoute>
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
      <Route path="/people" element={
        <ProtectedRoute><Layout><PeoplePage /></Layout></ProtectedRoute>
      } />
      <Route path="/messages" element={
        <ProtectedRoute><Layout><MessagesPage /></Layout></ProtectedRoute>
      } />
      <Route path="/shared-wardrobes" element={
        <ProtectedRoute><Layout><SharedWardrobesPage /></Layout></ProtectedRoute>
      } />
      <Route path="/shared-wardrobes/:id" element={
        <ProtectedRoute><Layout><SharedWardrobeDetailPage /></Layout></ProtectedRoute>
      } />
<Route path="/profile" element={
        <ProtectedRoute><Layout><ProfilePage /></Layout></ProtectedRoute>
      } />
      <Route path="/outfit-history" element={
        <ProtectedRoute><Layout><OutfitHistoryPage /></Layout></ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/" replace />} />
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
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <ToastRoot />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}