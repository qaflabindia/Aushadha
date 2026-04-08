import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { updateGlobalTargetUserEmail, updateGlobalPatientId } from '../API/Index';

interface Patient {
  case_id: string;
  age_group: string;
  sex: string;
  email: string | null;
}

interface PatientContextType {
  selectedPatient: Patient | null;
  setSelectedPatient: (patient: Patient | null) => void;
  isImpersonating: boolean;
  impersonatedEmail: string | null;
}

const PatientContext = createContext<PatientContextType | undefined>(undefined);

export const PatientProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(() => {
    const saved = localStorage.getItem('selectedPatient');
    return saved ? JSON.parse(saved) : null;
  });

  useEffect(() => {
    if (selectedPatient) {
      localStorage.setItem('selectedPatient', JSON.stringify(selectedPatient));
    } else {
      localStorage.removeItem('selectedPatient');
    }
    updateGlobalTargetUserEmail(selectedPatient?.email || null);
    updateGlobalPatientId(selectedPatient?.case_id || null);
  }, [selectedPatient]);

  const isImpersonating = selectedPatient !== null;
  const impersonatedEmail = selectedPatient?.email || null;

  return (
    <PatientContext.Provider value={{ selectedPatient, setSelectedPatient, isImpersonating, impersonatedEmail }}>
      {children}
    </PatientContext.Provider>
  );
};

export const usePatientContext = (): PatientContextType => {
  const context = useContext(PatientContext);
  if (context === undefined) {
    throw new Error('usePatientContext must be used within a PatientProvider');
  }
  return context;
};
