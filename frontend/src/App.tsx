import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DataProvider } from "./contexts/DataContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthProvider } from "./contexts/AuthContext";
import { SettingsProvider } from "./contexts/SettingsContext";
import './App.css'

import Layout from "./components/Layout";
import AuthLayout from "./components/AuthLayout";
import Home from './pages/Home';
import TrialSearch from './pages/Trials/Trials';
import TrialDetail from "./pages/Trials/TrialDetail";
import Community from './pages/Community/Community';
import PostDetails from './pages/Community/PostDetails';
import ResourceLibrary from './pages/Resources/ResourceLibrary';
import ResourceDetails from './pages/Resources/ResourceDetails';
import EventsHub from './pages/Events/EventsHub';
import EventDetails from './pages/Events/EventDetails';
import Assistant from './pages/Assistant';
import Profile from './pages/Profile';
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
                  <Route path="/trials" element={<TrialSearch />} />
                  <Route path="/trials/:id" element={<TrialDetail />} />
                  <Route path="/community" element={<Community />} />
                  <Route path="/community/posts/:id" element={<PostDetails />} />
                  <Route path="/resourcelibrary" element={<ResourceLibrary />} />
                  <Route path="/resources/:id" element={<ResourceDetails />} />
                  <Route path="/eventshub" element={<EventsHub />} />
                  <Route path="/events/:id" element={<EventDetails />} />
                  <Route path="/assistant" element={<Assistant />} />
                  <Route path="/profile" element={<Profile />} />
                </Route>

              </Routes>
            </BrowserRouter>
          </DataProvider>
        </SettingsProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
