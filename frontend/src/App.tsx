import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DataProvider } from "./contexts/DataContext";
import './App.css'

import Layout from "./components/Layout";
import Home from './pages/Home';
import TrialSearch from './pages/Trials';
import TrialDetail from "./pages/TrialDetail";
import Community from './pages/Community';
import ResourceLibrary from './pages/ResourceLibrary';
import EventsHub from './pages/EventsHub';
import Assistant from './pages/Assistant';
import Login from './pages/Login';
import Signup from './pages/Signup';

export default function App() {

  return (

    <DataProvider>

    <BrowserRouter>
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/trials" element={<TrialSearch />} />
        <Route path="/trials/:id" element={<TrialDetail />} />
        <Route path="/community" element={<Community />} />
        <Route path="/resourcelibrary" element={<ResourceLibrary />} />
        <Route path="/eventshub" element={<EventsHub />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
      </Route>
    </Routes>
    </BrowserRouter>
    </DataProvider>
  );
}
