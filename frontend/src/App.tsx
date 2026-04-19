import { Routes, Route, Navigate } from "react-router-dom";
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
import Login from './pages/Auth/Login';
import Signup from './pages/Auth/Signup';
import ForgotPassword from "./pages/Auth/ForgotPassword";
import ResetPassword from "./pages/Auth/ResetPassword";

export default function App() {
  return (
    <Routes>
      {/* Auth Routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
      </Route>

      {/* Protected / App Routes */}
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/trials" element={<Trials />} />
        <Route path="/trials/:id" element={<TrialDetail />} />
        <Route path="/community" element={<Community />} />
        <Route path="/community/posts/:id" element={<PostDetails />} />
        <Route path="/resources" element={<Resources />} />
        <Route path="/resources/:id" element={<ResourceDetails />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:id" element={<EventDetails />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/patientdashboard" element={<PatientDashboard />} />
        <Route path="/hcpdashboard" element={<HCPDashboard />} />
        <Route path="/notifications" element={<Notifications />} />
      </Route>

      {/* Redirects */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}