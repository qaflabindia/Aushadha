import React, { useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { url } from '../../utils/Utils';
import { usePatientContext } from '../../context/PatientContext';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { Typography } from '@neo4j-ndl/react';
import clsx from 'clsx';
import { RiUserShared2Line, RiArrowDownSLine } from 'react-icons/ri';

const PatientDropdown: React.FC = () => {
  const [patients, setPatients] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const { selectedPatient, setSelectedPatient } = usePatientContext();
  const { colorMode } = useContext(ThemeWrapperContext);

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const token = localStorage.getItem('aushadha_auth_token');
        if (!token) return;

        const response = await axios.get(`${url()}/rbac/my_patients`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        const validPatients = response.data.filter((p: any) => p.email != null);
        setPatients(validPatients);
      } catch (error) {
        console.error("Failed to fetch patients for dropdown", error);
      }
    };
    
    fetchPatients();
  }, []);

  return (
    <div className="relative">
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 rounded-full border transition-all cursor-pointer group glass-luxe min-w-[180px] justify-between',
          {
            'border-white/10 shadow-[0_0_10px_rgba(212,175,55,0.1)]': colorMode === 'dark',
            'border-gray-200': colorMode === 'light',
            'opacity-50 pointer-events-none': patients.length === 0 // Disable if no patients
          }
        )}
      >
        <div className="flex items-center gap-2">
          <RiUserShared2Line 
            className={clsx('text-sm transition-colors', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-gray-500': colorMode === 'light',
              'text-gray-400': patients.length === 0
            })}
          />
          <Typography variant="body-small" className={clsx('!m-0 text-xs font-semibold truncate max-w-[120px]', {
            'text-white': colorMode === 'dark' && patients.length > 0,
            'text-gray-800': colorMode === 'light' && patients.length > 0,
            'text-gray-400': patients.length === 0
          })}>
            {patients.length === 0 ? "No patients assigned" : (selectedPatient ? selectedPatient.case_id : "Select Patient")}
          </Typography>
        </div>
        <RiArrowDownSLine className={clsx("transition-transform", { "rotate-180": isOpen, "text-gray-400": colorMode === 'dark' })} />
      </div>

      {isOpen && patients.length > 0 && (
        <div className={clsx(
          "absolute top-full mt-2 w-full rounded-xl border overflow-hidden shadow-xl z-[100] transition-all",
          {
            "bg-[#1A1A1A]/90 backdrop-blur-md border-white/10": colorMode === 'dark',
            "bg-white border-gray-200": colorMode === 'light',
          }
        )}>
           <div 
              onClick={() => { setSelectedPatient(null); setIsOpen(false); }}
              className={clsx(
                "px-4 py-3 cursor-pointer text-xs transition-colors border-b",
                {
                  "hover:bg-white/10 text-white border-white/10": colorMode === 'dark',
                  "hover:bg-gray-100 text-gray-800 border-gray-100": colorMode === 'light',
                  "opacity-50": selectedPatient === null
                }
              )}
            >
              Reset Context (Global)
            </div>
          {patients.map(p => (
            <div 
              key={p.case_id}
              onClick={() => { setSelectedPatient(p); setIsOpen(false); }}
              className={clsx(
                "px-4 py-3 cursor-pointer text-xs transition-colors",
                {
                  "hover:bg-[#D4AF37]/20 text-white": colorMode === 'dark',
                  "hover:bg-blue-50 text-gray-800": colorMode === 'light',
                  "bg-[#D4AF37]/10": colorMode === 'dark' && selectedPatient?.case_id === p.case_id,
                  "bg-blue-100": colorMode === 'light' && selectedPatient?.case_id === p.case_id
                }
              )}
            >
              {p.case_id}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PatientDropdown;
