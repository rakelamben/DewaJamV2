import ShopPage from './app/customer/ShopPage'
import ProductPage from './app/customer/ProductPage'
import LoginPage from './app/customer/LoginPage'
import OrderPage from './app/customer/OrderPage'
import SignupPage from './app/customer/SignupPage'
import CartPage from './app/customer/CartPage'
import CheckoutPage from './app/customer/CheckoutPage'
import OrderDetailPage from './app/customer/OrderDetailPage'
import ProfilePage from './app/customer/ProfilePage'
import AddressPage from './app/customer/AddressPage'
import PaymentPage from './app/customer/PaymentPage'
import { Navigate, Routes, Route } from "react-router";
import LayoutPage from './app/internal/LayoutPage'
import DashboardPage from './app/internal/DashboardPage'
import POSpage from './app/internal/POSPage'
import SalesDailyPage from './app/internal/SalesDailyPage'
import WarehousePage from './app/internal/WarehousePage'
import MasterdataProductsPage from './app/internal/MasterdataProductsPage'
import MasterdataStoresPage from './app/internal/MasterdataStoresPage'
import InternalLoginPage from './app/internal/auth/LoginPage'
import NotificationsPage from './app/internal/NotificationsPage'
import ActivityLogsPage from './app/internal/ActivityLogsPage'
import PersonnelPage from './app/internal/PersonnelPage'
import MessagesPage from './app/internal/MessagesPage'
import DocumentsPage from './app/internal/DocumentsPage'
import WorkflowsPage from './app/internal/WorkflowsPage'
import CorrespondencePage from './app/internal/CorrespondencePage'
import KnowledgePage, { KnowledgeDetailPage } from './app/internal/KnowledgePage'
import MasterdataKnowledgePage from './app/internal/MasterdataKnowledgePage'
import SalesReportPage from './app/internal/SalesReportPage'
import ProfitabilityReportPage from './app/internal/ProfitabilityReportPage'
import InventoryReportPage from './app/internal/InventoryReportPage'
import KpiManagementPage from './app/internal/KpiManagementPage'
import { InternalAuthGuard } from './auth/InternalAuthGuard'
import DssOverviewPage from './app/internal/dss/DssOverviewPage'
import DssScenarioPage from './app/internal/dss/DssScenarioPage'
import DssWeightPage from './app/internal/dss/DssWeightPage'
import DssRunDetailPage from './app/internal/dss/DssRunDetailPage'
import EsOverviewPage from './app/internal/es/EsOverviewPage'
import EsDomainPage from './app/internal/es/EsDomainPage'
import EsRulesPage from './app/internal/es/EsRulesPage'
import ExpertAdvisorPage from './app/customer/ExpertAdvisorPage'

export default function AppRoutes() {
    return (
        <Routes >
            <Route path='/' element={<ShopPage />} /> 
            <Route path='/advisor' element={<ExpertAdvisorPage />} />
            <Route path='/product/:productId' element={<ProductPage />} /> 
            <Route path='/login' element={<LoginPage/>}></Route>
            <Route path='/signup' element={<SignupPage/>}></Route>
            <Route path='/cart' element={<CartPage/>}></Route>
            <Route path='/checkout' element={<CheckoutPage/>}></Route>
            <Route path='/orders' element={<OrderPage/>}></Route>
            <Route path='/orders/:transactionId' element={<OrderDetailPage/>}></Route>
            <Route path='/profile' element={<ProfilePage/>}></Route>
            <Route path='/profile/addresses' element={<AddressPage/>}></Route>
            <Route path='/payment/:state/:transactionId' element={<PaymentPage/>}></Route>
            <Route path='/internal' element={<InternalAuthGuard><LayoutPage /></InternalAuthGuard>}>
            
                 <Route index element={<DashboardPage />} />
                 <Route path='mis' element={<DashboardPage />} />
                 <Route path='mis/sales' element={<SalesReportPage />} />
                 <Route path='mis/profitability' element={<ProfitabilityReportPage />} />
                 <Route path='mis/inventory' element={<InventoryReportPage />} />
                 <Route path='mis/kpi' element={<KpiManagementPage />} />
                <Route path='pos' element={<Navigate to="/internal/pos/transaction" replace />} />
                <Route path='pos/transaction' element={<POSpage />} />
                <Route path='pos/sales' element={<SalesDailyPage />} />
                <Route path='warehouse' element={<WarehousePage />} />
                <Route path='notifications' element={<NotificationsPage />} />
                <Route path='activity-logs' element={<ActivityLogsPage />} />
                <Route path='personnel' element={<PersonnelPage />} />
                <Route path='messages' element={<MessagesPage />} />
                <Route path='documents' element={<DocumentsPage />} />
                <Route path='workflows' element={<WorkflowsPage />} />
                 <Route path='correspondence' element={<CorrespondencePage />} />
                 <Route path='knowledge' element={<KnowledgePage />} />
                 <Route path='knowledge/:knowledgeType/:itemId' element={<KnowledgeDetailPage />} />
                <Route path='masterdata' element={<Navigate to="/internal/masterdata/products" replace />} />
                <Route path='masterdata/products' element={<MasterdataProductsPage />} />
                 <Route path='masterdata/stores' element={<MasterdataStoresPage />} />
                 <Route path='masterdata/knowledge' element={<MasterdataKnowledgePage />} />
                 <Route path='dss' element={<DssOverviewPage />} />
                 <Route path='dss/:scenarioCode' element={<DssScenarioPage />} />
                 <Route path='dss/:scenarioCode/weights' element={<DssWeightPage />} />
                 <Route path='dss/runs/:runId' element={<DssRunDetailPage />} />
                 <Route path='es' element={<EsOverviewPage />} />
                 <Route path='es/:domainCode' element={<EsDomainPage />} />
                 <Route path='es/:domainCode/rules' element={<EsRulesPage />} />
            </Route>

            <Route path='/internal/login' element={<InternalLoginPage />}>

            </Route>
        </Routes>
    )
}
