import React, { useEffect, useMemo, useRef } from 'react';
import { Spotlight, SpotlightProvider, SpotlightTour, useSpotlightContext } from '@neo4j-ndl/react';
import { RiQuestionLine } from 'react-icons/ri';

// A guided tour for one page, like the one on the home dashboard. It runs by itself the
// first time someone opens the page, and the TourButton replays it. Each page has its own
// SpotlightProvider, so these tours never mix with the home tour.

export interface PageTourStep {
  target: string; // id of a SpotlightTarget on the page
  title: string;
  body: string;
}

const seenKey = (tourId: string) => `aushadha.tour.${tourId}.seen`;

const hasSeen = (tourId: string): boolean => {
  try {
    return localStorage.getItem(seenKey(tourId)) !== null;
  } catch {
    return true; // storage blocked: don't keep popping the tour up
  }
};

const markSeen = (tourId: string) => {
  try {
    localStorage.setItem(seenKey(tourId), '1');
  } catch {
    // storage blocked: nothing to remember
  }
};

const TourContext = React.createContext<{ start: () => void }>({ start: () => {} });

const TourRunner: React.FC<{
  tourId: string;
  steps: PageTourStep[];
  autoStart: boolean;
  children: React.ReactNode;
}> = ({ tourId, steps, autoStart, children }) => {
  const { setActiveSpotlight, setIsOpen, registeredTargets } = useSpotlightContext();
  const started = useRef(false);

  // Only steps whose target is on screen (e.g. tabs hidden for some roles are skipped)
  const visibleSteps = useMemo(
    () => steps.filter((s) => Boolean(registeredTargets[s.target])),
    [steps, registeredTargets]
  );

  // Open the first step's popover straight away
  const start = () => {
    if (visibleSteps.length > 0) {
      setActiveSpotlight(visibleSteps[0].target);
      setIsOpen(true);
    }
  };

  // First visit: start once the first step's target is on the page (pages may still be loading)
  useEffect(() => {
    if (!autoStart || started.current || hasSeen(tourId) || visibleSteps.length === 0) {
      return;
    }
    if (visibleSteps[0].target !== steps[0]?.target) {
      return;
    }
    started.current = true;
    markSeen(tourId);
    setActiveSpotlight(visibleSteps[0].target);
    setIsOpen(true);
  }, [autoStart, tourId, steps, visibleSteps, setActiveSpotlight, setIsOpen]);

  const spotlights = useMemo(
    () =>
      visibleSteps.map((s) => ({
        target: s.target,
        children: (
          <>
            <Spotlight.Header>{s.title}</Spotlight.Header>
            <Spotlight.Body>{s.body}</Spotlight.Body>
          </>
        ),
      })),
    [visibleSteps]
  );

  return (
    <TourContext.Provider value={{ start }}>
      {children}
      {spotlights.length > 0 && <SpotlightTour spotlights={spotlights} />}
    </TourContext.Provider>
  );
};

export const PageTour: React.FC<{
  tourId: string;
  steps: PageTourStep[];
  autoStart?: boolean;
  children: React.ReactNode;
}> = ({ tourId, steps, autoStart = true, children }) => (
  <SpotlightProvider>
    <TourRunner tourId={tourId} steps={steps} autoStart={autoStart}>
      {children}
    </TourRunner>
  </SpotlightProvider>
);

// Replays the page's tour. Must be inside a PageTour.
export const TourButton: React.FC<{ label: string; className?: string }> = ({ label, className }) => {
  const { start } = React.useContext(TourContext);
  return (
    <button
      type='button'
      onClick={start}
      title={label}
      aria-label={label}
      className={
        className ??
        'inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold opacity-70 hover:opacity-100 transition-opacity'
      }
    >
      <RiQuestionLine className='w-4 h-4' />
      {label}
    </button>
  );
};

export default PageTour;
