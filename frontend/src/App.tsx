import { BrowserRouter, Routes, Route } from "react-router-dom";
import './App.css'

import Layout from "./components/Layout";
import Home from './pages/Home';
import TrialSearch from './pages/TrialSearch';
import Community from './pages/Community';
import ResourceLibrary from './pages/ResourceLibrary';
import EventsHub from './pages/EventsHub';
import Assistant from './pages/Assistant';
import UserProfile from './pages/UserProfile';

export default function App() {

  return (

    <BrowserRouter>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/trialsearch" element={<TrialSearch />} />
        <Route path="/community" element={<Community />} />
        <Route path="/resourcelibrary" element={<ResourceLibrary />} />
        <Route path="/eventshub" element={<EventsHub />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/userprofile" element={<UserProfile />} />
      </Route>
    </Routes>
    </BrowserRouter>
  );
}
