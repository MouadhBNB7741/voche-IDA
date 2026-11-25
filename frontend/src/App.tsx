import { Routes, Route } from "react-router-dom";
import './App.css'

import Layout from "./components/Layout";
import AuthLayout from "./components/AuthLayout";
import Home from './pages/Home';
import Trials from './pages/Trials/Trials';
import TrialDetail from "./pages/Trials/TrialDetail";
import Community from './pages/Community/Community';
import PostDetails from './pages/Community/PostDetails';
import Resources from './pages/Resources/Resources';
import ResourceDetails from './pages/Resources/ResourceDetails';
import Events from './pages/Events/Events';
import EventDetails from './pages/Events/EventDetails';
import Assistant from './pages/Assistant';
import PatientDashboard from './pages/PatientDashboard/PatientDashboard';
import HCPDashboard from './pages/HCPDashboard/HCPDashboard';
import Notifications from './pages/Notifications';
import AdminDashboard from './pages/Admin/AdminDashboard';
import Surveys from './pages/Surveys/Surveys';
import SurveyRunner from './pages/Surveys/SurveyRunner';
import SurveyBuilder from './pages/Surveys/SurveyBuilder';
import Login from './pages/Auth/Login';
import Signup from './pages/Auth/Signup';
import ForgotPassword from "./pages/Auth/ForgotPassword";
import ResetPassword from "./pages/Auth/ResetPassword";
import Onboarding from "./pages/Auth/Onboarding";
import ProfileRedirect from "./pages/ProfileRedirect";
import NotFound from "./pages/Error/NotFound";
import Forbidden from "./pages/Error/Forbidden";

export default function App() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/profile" element={<ProfileRedirect />} />
      </Route>

      {/* Protected / App Routes */}
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/trials" element={<Trials />} />
        <Route path="/trials/:id" element={<TrialDetail />} />
        <Route path="/community" element={<Community />} />
        <Route path="/community/:communityId/posts/:postId" element={<PostDetails />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/resources/:id" element={<ResourceDetails />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:id" element={<EventDetails />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/patientdashboard" element={<PatientDashboard />} />
        <Route path="/hcpdashboard" element={<HCPDashboard />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/surveys" element={<Surveys />} />
        <Route path="/surveys/manage" element={<SurveyBuilder />} />
        <Route path="/surveys/:id/take" element={<SurveyRunner />} />
        <Route path="/403" element={<Forbidden />} />
        <Route path="/404" element={<NotFound />} />
      </Route>

      {/* Wildcard Error Page */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}