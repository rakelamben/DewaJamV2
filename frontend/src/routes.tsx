import ShopPage from './app/customer/ShopPage'
import ProductPage from './app/customer/ProductPage'
import LoginPage from './app/customer/LoginPage'
import OrderPage from './app/customer/OrderPage'
import SignupPage from './app/customer/SignupPage'
import CartPage from './app/customer/CartPage'
import { Routes, Route } from "react-router";
import LayoutPage from './app/internal/LayoutPage'
import DashboardPage from './app/internal/DashboardPage'
import POSpage from './app/internal/DashboardPage'
import WarehousePage from './app/internal/DashboardPage'
import MasterdataPage from './app/internal/DashboardPage'
import InternalLoginPage from './app/internal/auth/LoginPage'
import { InternalAuthGuard } from './auth/InternalAuthGuard'

export default function AppRoutes() {
    return (
        <Routes >
            <Route path='/' element={<ShopPage />} /> 
            <Route path='/product/:productId' element={<ProductPage />} /> 
            <Route path='/login' element={<LoginPage/>}></Route>
            <Route path='/signup' element={<SignupPage/>}></Route>
            <Route path='/cart' element={<CartPage/>}></Route>
            <Route path='/orders' element={<OrderPage/>}></Route>
            <Route path='/internal' element={<InternalAuthGuard><LayoutPage /></InternalAuthGuard>}>
            
            <Route index element={<DashboardPage />} />
                <Route path='pos' element={<POSpage />} />
                <Route path='warehouse' element={<WarehousePage />} />
                <Route path='masterdata' element={<MasterdataPage />} />
            </Route>

            <Route path='/internal/login' element={<InternalLoginPage />}>

            </Route>
        </Routes>
    )
}
