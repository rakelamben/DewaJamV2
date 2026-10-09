import './App.css'
import AppRoutes from './routes'
import { BrowserRouter} from "react-router";
import { AuthProvider } from './auth/AuthContext'


function App() {

  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
    
  )
}

export default App
