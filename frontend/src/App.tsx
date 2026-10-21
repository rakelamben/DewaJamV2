import './App.css'
import AppRoutes from './routes'
import { BrowserRouter} from "react-router";
import { AuthProvider } from './auth/AuthContext'
import { Toaster } from '@/components/ui/sonner'
import { CustomerAuthProvider } from './auth/CustomerAuthContext'


function App() {

  return (
    <BrowserRouter>
      <AuthProvider>
        <CustomerAuthProvider>
          <AppRoutes />
          <Toaster />
        </CustomerAuthProvider>
      </AuthProvider>
    </BrowserRouter>
    
  )
}

export default App
