import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import Home from "./pages/Home";
import Discover from "./pages/Discover";
import MovieDetails from "./pages/MovieDetails";
import Personalized from "./pages/Personalized";
import Onboarding from "./pages/Onboarding";
import Favorites from "./pages/Favorites";
import MyRatings from "./pages/MyRatings";
import ModelInsights from "./pages/ModelInsights";
import About from "./pages/About";
import { ErrorState } from "./components/ui";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/discover" element={<Discover />} />
        <Route path="/movies/:id" element={<MovieDetails />} />
        <Route path="/for-you" element={<Personalized />} />
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/favorites" element={<Favorites />} />
        <Route path="/ratings" element={<MyRatings />} />
        <Route path="/insights" element={<ModelInsights />} />
        <Route path="/about" element={<About />} />
        <Route
          path="*"
          element={
            <ErrorState
              title="Page not found"
              message="The route you tried does not exist."
            />
          }
        />
      </Route>
    </Routes>
  );
}
