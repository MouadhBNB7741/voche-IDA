import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DataProvider } from "./contexts/DataContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import { SettingsProvider } from "./contexts/SettingsContext";
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
import Profile from './pages/Profile';
import Notifications from './pages/Notifications';
import Login from './pages/Auth/Login';
import Signup from './pages/Auth/Signup';


export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <SettingsProvider>
          <DataProvider>
            <BrowserRouter>
              <Routes>

                <Route element={<AuthLayout />}>
                  <Route path="/login" element={<Login />} />
                  <Route path="/signup" element={<Signup />} />
                </Route>

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
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/notifications" element={<Notifications />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/signup" element={<Signup />} />
                </Route>

              </Routes>
            </BrowserRouter>
          </DataProvider>
        </SettingsProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
