import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DataProvider } from "./contexts/DataContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import './App.css'

import Layout from "./components/Layout";
import Home from './pages/Home';
import TrialSearch from './pages/Trials';
import TrialDetail from "./pages/TrialDetail";
import Community from './pages/Community/Community';
import PostDetails from './pages/Community/PostDetails';
import ResourceLibrary from './pages/Resources/ResourceLibrary';
import ResourceDetails from './pages/Resources/ResourceDetails';
import EventsHub from './pages/Events/EventsHub';
import EventDetails from './pages/Events/EventDetails';
import Assistant from './pages/Assistant';
import Login from './pages/Login';
import Signup from './pages/Signup';

export default function App() {

  return (

    <ThemeProvider>
      <DataProvider>
        <BrowserRouter>
          <Routes>
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
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </DataProvider>
    </ThemeProvider>
  );
}
