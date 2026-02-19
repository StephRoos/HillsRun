"use client";

import { createContext, useContext, useState, useCallback } from "react";

interface CoachContextValue {
  athleteUserId: number | null;
  athleteName: string | null;
  setAthlete: (userId: number | null, name: string | null) => void;
  isViewingAthlete: boolean;
}

const CoachContext = createContext<CoachContextValue>({
  athleteUserId: null,
  athleteName: null,
  setAthlete: () => {},
  isViewingAthlete: false,
});

export function CoachProvider({ children }: { children: React.ReactNode }) {
  const [athleteUserId, setAthleteUserId] = useState<number | null>(null);
  const [athleteName, setAthleteName] = useState<string | null>(null);

  const setAthlete = useCallback(
    (userId: number | null, name: string | null) => {
      setAthleteUserId(userId);
      setAthleteName(name);
    },
    []
  );

  return (
    <CoachContext.Provider
      value={{
        athleteUserId,
        athleteName,
        setAthlete,
        isViewingAthlete: athleteUserId !== null,
      }}
    >
      {children}
    </CoachContext.Provider>
  );
}

export function useCoachContext() {
  return useContext(CoachContext);
}
