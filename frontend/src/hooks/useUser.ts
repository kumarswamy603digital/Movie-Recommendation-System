// Small local hooks: current user id (persisted in localStorage) and theme toggle.

import { useCallback, useEffect, useState } from "react";
import { DEMO_USER_ID } from "../api/client";

const USER_KEY = "mr.user_id";
const THEME_KEY = "mr.theme";

export function useUser() {
  const [userId, setUserId] = useState<number>(() => {
    if (typeof window === "undefined") return DEMO_USER_ID;
    const raw = window.localStorage.getItem(USER_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) && n > 0 ? n : DEMO_USER_ID;
  });

  const update = useCallback((n: number) => {
    const v = Number.isFinite(n) && n > 0 ? Math.trunc(n) : DEMO_USER_ID;
    setUserId(v);
    if (typeof window !== "undefined") window.localStorage.setItem(USER_KEY, String(v));
  }, []);

  return { userId, setUserId: update };
}

export function useTheme() {
  const [dark, setDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    const stored = window.localStorage.getItem(THEME_KEY);
    return stored === null ? true : stored === "dark";
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) root.classList.add("dark");
    else root.classList.remove("dark");
    if (typeof window !== "undefined") {
      window.localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
    }
  }, [dark]);

  return { dark, toggle: () => setDark((d) => !d) };
}
