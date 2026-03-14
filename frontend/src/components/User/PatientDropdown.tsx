import React, { useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';
import { url } from '../../utils/Utils';
import { usePatientContext } from '../../context/PatientContext';
import { ThemeWrapperContext } from '../../context/ThemeWrapper';
import { Typography } from '@neo4j-ndl/react';
import clsx from 'clsx';
import { RiArrowDownSLine, RiShieldUserLine, RiRefreshLine } from 'react-icons/ri';

const PatientDropdown: React.FC = () => {
  const [patients, setPatients] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const { selectedPatient, setSelectedPatient } = usePatientContext();
  const { colorMode } = useContext(ThemeWrapperContext);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const token = localStorage.getItem('aushadha_auth_token');
        if (!token) {
          return;
        }

        const response = await axios.get(`${url()}/rbac/my_patients`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        const validPatients = response.data.filter((p: any) => p.email != null);
        setPatients(validPatients);
      } catch (error) {
        console.error('Failed to fetch patients for dropdown', error);
      }
    };

    fetchPatients();
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className='relative' ref={dropdownRef}>
      <div
        onClick={() => patients.length > 0 && setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-2 px-5 py-2 rounded-full border transition-all duration-500 cursor-pointer group glass-luxe min-w-[200px] justify-between',
          {
            // Dark Mode Trigger
            'bg-black/40 border-white/10 shadow-[0_0_20px_rgba(212,175,55,0.05)] hover:border-[#D4AF37]/40':
              colorMode === 'dark',
            'border-[#D4AF37] shadow-[0_0_25px_rgba(212,175,55,0.15)]': colorMode === 'dark' && isOpen,

            // Light Mode Trigger
            'bg-white/80 border-gray-200 shadow-sm hover:border-blue-400': colorMode === 'light',
            'border-blue-500 ring-2 ring-blue-500/10': colorMode === 'light' && isOpen,

            'opacity-50 cursor-not-allowed': patients.length === 0,
          }
        )}
      >
        <div className='flex items-center gap-2.5 overflow-hidden'>
          <RiShieldUserLine
            className={clsx('text-base transition-colors duration-500', {
              'text-[#D4AF37]': colorMode === 'dark',
              'text-blue-600': colorMode === 'light',
              'opacity-40': patients.length === 0,
            })}
          />
          <div className='flex flex-col truncate'>
            <span
              className={clsx('text-[8px] uppercase tracking-[0.2em] font-bold opacity-50', {
                'text-[#D4AF37]': colorMode === 'dark',
                'text-blue-700': colorMode === 'light',
              })}
            >
              {selectedPatient ? 'Active Patient' : 'Patient Context'}
            </span>
            <Typography
              variant='body-small'
              className={clsx('!m-0 text-[11px] font-bold truncate tracking-wide', {
                'text-white': colorMode === 'dark' && patients.length > 0,
                'text-gray-900': colorMode === 'light' && patients.length > 0,
                'text-gray-400': patients.length === 0,
              })}
            >
              {patients.length === 0
                ? 'No patients found'
                : selectedPatient
                  ? selectedPatient.case_id
                  : 'Select Case ID'}
            </Typography>
          </div>
        </div>
        <RiArrowDownSLine
          className={clsx('w-4 h-4 transition-transform duration-500', {
            'rotate-180': isOpen,
            'text-[#D4AF37]': colorMode === 'dark',
            'text-blue-600': colorMode === 'light',
            'opacity-30': patients.length === 0,
          })}
        />
      </div>

      {isOpen && patients.length > 0 && (
        <div
          className={clsx(
            'absolute top-full mt-3 w-full rounded-2xl border shadow-[0_20px_50px_rgba(0,0,0,0.5)] z-[1000] animate-inc-scale origin-top overflow-hidden',
            {
              '!bg-[#0F1014] border-[#D4AF37]/20': colorMode === 'dark',
              '!bg-white border-gray-100 shadow-xl': colorMode === 'light',
            }
          )}
        >
          {/* Header/Utility Section */}
          <div
            onClick={() => {
              setSelectedPatient(null);
              setIsOpen(false);
            }}
            className={clsx(
              'flex items-center gap-2 px-5 py-3.5 cursor-pointer text-[10px] font-bold uppercase tracking-widest transition-all border-b',
              {
                'hover:bg-[#D4AF37]/10 text-[#D4AF37] border-white/5': colorMode === 'dark',
                'hover:bg-blue-50 text-blue-600 border-gray-50': colorMode === 'light',
                'opacity-40': selectedPatient === null,
              }
            )}
          >
            <RiRefreshLine size={14} className='animate-spin-slow' />
            Reset Context (Global)
          </div>

          <div className='max-h-[300px] overflow-y-auto premium-scrollbar'>
            {patients.map((p) => {
              const isSelected = selectedPatient?.case_id === p.case_id;
              return (
                <div
                  key={p.case_id}
                  onClick={() => {
                    setSelectedPatient(p);
                    setIsOpen(false);
                  }}
                  className={clsx(
                    'group flex items-center justify-between px-5 py-3.5 cursor-pointer transition-all duration-300',
                    {
                      // Dark Mode Item
                      'hover:bg-[#D4AF37]/10': colorMode === 'dark',
                      'bg-[#D4AF37]/5': colorMode === 'dark' && isSelected,

                      // Light Mode Item
                      'hover:bg-blue-50/50': colorMode === 'light',
                      'bg-blue-50': colorMode === 'light' && isSelected,
                    }
                  )}
                >
                  <div className='flex flex-col'>
                    <span
                      className={clsx('text-xs font-bold transition-colors tracking-wide', {
                        'text-white': colorMode === 'dark' && isSelected,
                        'text-white/60 group-hover:text-white': colorMode === 'dark' && !isSelected,
                        'text-blue-900': colorMode === 'light' && isSelected,
                        'text-gray-700 group-hover:text-gray-900': colorMode === 'light' && !isSelected,
                      })}
                    >
                      {p.case_id}
                    </span>
                    <span
                      className={clsx('text-[9px] opacity-40 mt-0.5', {
                        'text-white': colorMode === 'dark',
                        'text-gray-500': colorMode === 'light',
                      })}
                    >
                      {p.email}
                    </span>
                  </div>

                  {isSelected && (
                    <div
                      className={clsx('w-1.5 h-1.5 rounded-full shadow-[0_0_10px_rgba(212,175,55,0.8)]', {
                        'bg-[#D4AF37]': colorMode === 'dark',
                        'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]': colorMode === 'light',
                      })}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default PatientDropdown;
