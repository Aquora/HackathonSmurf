import { useEffect, useState } from "react";
import { AppHeader } from "./components/AppHeader/AppHeader";
import { LandingPage, SIGN_UP_HREF } from "./features/landing/LandingPage";

function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return hash;
}

export function App() {
  const route = useHashRoute();

  return (
    <>
      <AppHeader />
      {route === SIGN_UP_HREF ? (
        // Placeholder until the "LocalQuest sign up" frame is implemented.
        <main className="placeholder-page">
          <p>Sign up is not built yet.</p>
          <a href="#/">Back to start</a>
        </main>
      ) : (
        <LandingPage />
      )}
    </>
  );
}
