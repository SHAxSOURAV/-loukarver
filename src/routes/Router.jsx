import { createBrowserRouter } from "react-router-dom";
import React, { Suspense } from "react";
import DashboardLayout from "../layout/dashboardLayout/DashboardLayout";
import ProtectedRoute from "../protectedRoute/ProtectedRoute";

// Lazy load all page components to prevent a single blocked module
// (e.g. by ad-blockers) from crashing the entire app
const Dashboard = React.lazy(() => import("../components/Dashboard/Dashboard"));
const UserManagement = React.lazy(() => import("../page/UserManagement/UserManagement"));
const CreatorManagement = React.lazy(() => import("../page/CreatorManagement/CreatorManagement"));
const Subscription = React.lazy(() => import("../page/Subscription/Subscription"));
const Profile = React.lazy(() => import("../page/Settings/Profile"));
const TermsCondition = React.lazy(() => import("../page/Settings/TermsCondition"));
const FAQ = React.lazy(() => import("../page/Settings/FAQ"));
const PrivacyPolicy = React.lazy(() => import("../page/Settings/PrivacyPolicy"));
const Categories = React.lazy(() => import("../page/CategoriesManagement/Categories"));
const Subcategory = React.lazy(() => import("../page/CategoriesManagement/Subcategory"));
const ForgetPass = React.lazy(() => import("../Auth/ForgetPass"));
const Verify = React.lazy(() => import("../Auth/Verify"));
const ResetPass = React.lazy(() => import("../Auth/ResetPass"));
const Notification = React.lazy(() => import("../page/Notification/Notification"));
const About = React.lazy(() => import("../page/Settings/About"));
const Login = React.lazy(() => import("../Auth/Login"));
const Analytics = React.lazy(() => import("../page/appInsights/Analytics"));
const Collaboration = React.lazy(() => import("../page/collaboration/Collaboration"));
const Transaction = React.lazy(() => import("../page/transaction/Transaction"));
const Report = React.lazy(() => import("../page/report/Report"));
const Signup = React.lazy(() => import("../Auth/Signup"));

// Fallback component shown while lazy-loaded components are loading
const LazyFallback = () => (
  <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
    <div style={{ width: "40px", height: "40px", border: "4px solid #e5e7eb", borderTop: "4px solid #8B4513", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

// Wrap element in Suspense for lazy loading
const withSuspense = (Component) => (
  <Suspense fallback={<LazyFallback />}>
    <Component />
  </Suspense>
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <DashboardLayout></DashboardLayout>
      </ProtectedRoute>
    ),
    children: [
      {
        path: "/",
        element: withSuspense(Dashboard),
      },
      {
        path: "/dashboard/UserManagement",
        element: withSuspense(UserManagement),
      },
      {
        path: "/dashboard/analytics",
        element: withSuspense(Analytics),
      },
       {
        path: "/dashboard/collaboration",
        element: withSuspense(Collaboration),
      },
       {
        path: "/dashboard/transaction",
        element: withSuspense(Transaction),
      },
       {
        path: "/dashboard/report",
        element: withSuspense(Report),
      },
      {
        path: "/dashboard/CreatorManagement",
        element: withSuspense(CreatorManagement),
      },
      {
        path: "/dashboard/CategoriesManagement/Categories",
        element: withSuspense(Categories),
      },
      {
        path: "/dashboard/CategoriesManagement/Subcategory",
        element: withSuspense(Subcategory),
      },
      {
        path: "/dashboard/Subscription",
        element: withSuspense(Subscription),
      },
      {
        path: "/dashboard/Settings/profile",
        element: withSuspense(Profile),
      },
      {
        path: "/dashboard/Settings/notification",
        element: withSuspense(Notification),
      },
      {
        path: "/dashboard/Settings/Terms&Condition",
        element: withSuspense(TermsCondition),
      },
      {
        path: "/dashboard/Settings/FAQ",
        element: withSuspense(FAQ),
      },
      {
        path: "/dashboard/Settings/aboutUs",
        element: withSuspense(About),
      },
      {
        path: "/dashboard/Settings/PrivacyPolicy",
        element: withSuspense(PrivacyPolicy),
      },
    ],
  },

  {
    path: "/login",
    element: withSuspense(Login),
  },
  {
    path: "/signup",
    element: withSuspense(Signup),
  },
  {
    path: "/forgot-password",
    element: withSuspense(ForgetPass),
  },
  {
    path: "/verification",
    element: withSuspense(Verify),
  },
  {
    path: "/reset-password",
    element: withSuspense(ResetPass),
  },
]);
