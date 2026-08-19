import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { SolvePage } from './pages/SolvePage'
import { JobPage } from './pages/JobPage'
import { HistoryPage } from './pages/HistoryPage'
import { TokensPage } from './pages/TokensPage'
import { UsersPage } from './pages/UsersPage'
import { BatchUploadPage } from './pages/BatchUploadPage'
import { BatchDetailPage } from './pages/BatchDetailPage'
import { ComparePage } from './pages/ComparePage'
import { CompareBatchesPage } from './pages/CompareBatchesPage'
import { SystemStatusProvider } from './status/SystemStatusContext'

export default function App() {
  return (
    <AuthProvider>
      <SystemStatusProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/solve"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <SolvePage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/jobs/:jobId"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <JobPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/batches/new"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <BatchUploadPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/batches/:batchId"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <BatchDetailPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/compare"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <ComparePage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/compare/batches"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <CompareBatchesPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <Layout wide>
                  <HistoryPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tokens"
            element={
              <ProtectedRoute>
                <Layout>
                  <TokensPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute>
                <Layout>
                  <UsersPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/solve" replace />} />
        </Routes>
      </SystemStatusProvider>
    </AuthProvider>
  )
}
