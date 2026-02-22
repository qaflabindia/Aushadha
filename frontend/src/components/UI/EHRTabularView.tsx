import React, { useState } from 'react';
import { 
  CloudArrowUpIcon, 
  PencilSquareIcon, 
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

interface Vital {
  name: string;
  value: number;
  unit: string;
  status: string;
}

interface LifestyleFactor {
  name: string;
  status: string;
}

interface Symptom {
  name: string;
  status: string;
}

interface EHRRecord {
  case_id: string;
  visit_date: string;
  age_group: string;
  sex: string;
  condition_name: string;
  chief_complaint: string;
  red_flag_any: boolean;
  red_flag_details: string[];
  vitals: Vital[];
  symptoms: Symptom[];
  lifestyle_factors?: LifestyleFactor[];
}

interface Props {
  data: EHRRecord[];
  onUpdate: (caseId: string, updatedData: Partial<EHRRecord>) => Promise<void>;
  onSync: (caseId: string) => Promise<void>;
}

const EHRTabularView: React.FC<Props> = ({ data, onUpdate, onSync }) => {
  const [syncing, setSyncing] = useState<string | null>(null);
  const [editingRecord, setEditingRecord] = useState<EHRRecord | null>(null);

  const handleSyncClick = async (caseId: string) => {
    setSyncing(caseId);
    await onSync(caseId);
    setSyncing(null);
  };

  const handleUpdateClick = async () => {
    if (editingRecord) {
      await onUpdate(editingRecord.case_id, editingRecord);
      setEditingRecord(null);
    }
  };

  if (data.length === 0) {
    return (
      <div className="glass-panel p-20 text-center text-gray-400 fade-in">
        <div className="text-xl font-medium mb-2">Primary Ingestion Pending</div>
        <p className="text-sm opacity-60">Upload clinical transcripts or scans to populate the EHRS Postgres View.</p>
      </div>
    );
  }

  // Extract all unique vital names across all records for dynamic columns
  const allVitalNames = Array.from(new Set(data.flatMap(r => r.vitals.map(v => v.name))));

  return (
    <div className="w-full overflow-hidden glass-panel fade-in-up relative">
      <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/2">
        <h3 className="text-sm uppercase tracking-widest font-bold text-[#F5A623]">EHRS Postgres Master View</h3>
        <div className="flex gap-2 text-[10px] items-center text-gray-500">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span> Normal</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500"></span> Elevated</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> Critical</span>
        </div>
      </div>
      
      <div className="overflow-x-api custom-scrollbar">
        <table className="w-full text-left border-collapse min-w-[1200px]">
          <thead>
            <tr className="bg-black/40 text-[11px] uppercase tracking-tighter text-gray-400 border-b border-white/10">
              <th className="px-4 py-4 font-semibold sticky left-0 bg-black/60 z-10 backdrop-blur-md">Case ID</th>
              <th className="px-4 py-4 font-semibold">Visit Date</th>
              <th className="px-4 py-4 font-semibold">Ailment/Condition</th>
              <th className="px-4 py-4 font-semibold">Sex</th>
              {allVitalNames.map(name => (
                <th key={name} className="px-4 py-4 font-semibold text-center">{name}</th>
              ))}
              <th className="px-4 py-4 font-semibold">Symptoms</th>
              <th className="px-4 py-4 font-semibold">Lifestyle Suspicions</th>
              <th className="px-4 py-4 font-semibold">Red Flag</th>
              <th className="px-4 py-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="text-sm text-gray-300">
            {data.map((record) => (
              <tr key={record.case_id} className="border-b border-white/5 hover:bg-white/5 transition-colors group">
                <td className="px-4 py-4 font-mono font-bold text-white sticky left-0 bg-black/40 group-hover:bg-black/60 z-10 backdrop-blur-md">
                  {record.case_id}
                </td>
                <td className="px-4 py-4 opacity-70 whitespace-nowrap">{record.visit_date}</td>
                <td className="px-4 py-4">
                  <span className="text-[#F5A623] font-medium">{record.condition_name}</span>
                </td>
                <td className="px-4 py-4 opacity-70">{record.sex}</td>
                
                {allVitalNames.map(vitalName => {
                  const vital = record.vitals.find(v => v.name === vitalName);
                  return (
                    <td key={vitalName} className="px-4 py-4 text-center">
                      {vital ? (
                        <div className="flex flex-col items-center">
                          <span className={`text-sm font-bold drop-shadow-[0_0_8px_rgba(245,166,35,0.2)] ${
                            vital.status === 'CrisisSuspected' ? 'text-red-500 animate-pulse' :
                            vital.status === 'Stage2' ? 'text-orange-500' :
                            vital.status === 'Stage1' ? 'text-yellow-500' :
                            vital.status === 'Elevated' ? 'text-amber-400' :
                            'text-green-400 font-medium'
                          }`}>
                            {vital.value}
                          </span>
                          <span className="text-[9px] text-gray-600 font-mono tracking-tighter uppercase">{vital.unit}</span>
                        </div>
                      ) : (
                        <span className="text-white/10">—</span>
                      )}
                    </td>
                  );
                })}

                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1 max-w-[150px]">
                    {record.symptoms.slice(0, 3).map((s, i) => (
                      <span key={i} className={`px-2 py-0.5 rounded text-[10px] border ${
                        s.status === 'True' ? 'bg-indigo-500/10 border-indigo-400/30 text-indigo-300 shadow-[0_0_10px_rgba(99,102,241,0.2)]' :
                        s.status === 'False' ? 'bg-white/5 border-white/5 text-gray-600 opacity-40' :
                        'border-white/10 border-dashed text-gray-500'
                      }`}>
                        {s.name}
                      </span>
                    ))}
                  </div>
                </td>

                <td className="px-4 py-4">
                  <div className="flex flex-wrap gap-1 max-w-[150px]">
                    {record.lifestyle_factors?.slice(0, 3).map((l, i) => (
                      <span key={i} className={`px-2 py-0.5 rounded text-[10px] border ${
                        l.status === 'True' ? 'bg-amber-500/10 border-amber-400/30 text-amber-300' :
                        l.status === 'False' ? 'bg-white/5 border-white/5 text-gray-600 opacity-40' :
                        'border-white/10 border-dashed text-gray-500'
                      }`}>
                        {l.name}
                      </span>
                    ))}
                  </div>
                </td>

                <td className="px-4 py-4 text-center">
                  {record.red_flag_any ? (
                    <div className="flex justify-center">
                       <ExclamationTriangleIcon className="w-5 h-5 text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.5)] animate-pulse" />
                    </div>
                  ) : (
                    <CheckCircleIcon className="w-5 h-5 text-green-500/20 mx-auto" />
                  )}
                </td>

                <td className="px-4 py-4 text-right">
                  <div className="flex justify-end gap-3 opacity-40 group-hover:opacity-100 transition-opacity">
                    <button 
                      onClick={() => setEditingRecord(record)}
                      className="p-1 hover:text-[#F5A623] transition-colors"
                      title="Edit Record"
                    >
                      <PencilSquareIcon className="w-5 h-5" />
                    </button>
                    <button 
                      onClick={() => handleSyncClick(record.case_id)}
                      disabled={syncing === record.case_id}
                      className={`p-1 hover:text-indigo-400 transition-colors ${syncing === record.case_id ? 'animate-spin text-indigo-400' : ''}`}
                      title="Synchronize to Knowledge Graph"
                    >
                      <CloudArrowUpIcon className="w-5 h-5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editingRecord && (
        <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/40 backdrop-blur-md p-4 sm:p-0">
          <div className="glass-panel max-w-4xl w-full p-8 space-y-8 shadow-[0_-20px_50px_rgba(0,0,0,0.5)] border-t border-white/10 rounded-t-3xl slide-in-bottom">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-2xl font-bold bg-gradient-to-r from-[#F5A623] to-[#E09612] bg-clip-text text-transparent">
                  Clinical Refinement Terminal
                </h4>
                <div className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Authenticating Case: {editingRecord.case_id}</div>
              </div>
              <button onClick={() => setEditingRecord(null)} className="p-2 hover:bg-white/5 rounded-full transition-colors text-gray-500 hover:text-white">
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="space-y-2">
                  <label className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">Ailment/Condition</label>
                  <input 
                    className="w-full bg-black/40 border border-white/5 rounded-xl p-4 text-sm focus:border-[#F5A623] outline-none transition-all shadow-inner"
                    value={editingRecord.condition_name}
                    onChange={(e) => setEditingRecord({ ...editingRecord, condition_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">Chief Complaint</label>
                  <textarea 
                    className="w-full bg-black/40 border border-white/5 rounded-xl p-4 text-sm focus:border-[#F5A623] outline-none min-h-[100px] transition-all shadow-inner"
                    value={editingRecord.chief_complaint}
                    onChange={(e) => setEditingRecord({ ...editingRecord, chief_complaint: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-6 overflow-y-auto max-h-[400px] pr-2 custom-scrollbar">
                <h5 className="text-[10px] uppercase font-bold text-gray-500 tracking-widest border-b border-white/5 pb-2">Vitals & Metrics</h5>
                <div className="grid grid-cols-2 gap-4">
                  {editingRecord.vitals.map((v, i) => (
                    <div key={i} className="bg-white/2 p-3 rounded-xl border border-white/5 hover:border-white/10 transition-all">
                      <div className="text-[9px] text-gray-500 uppercase mb-2">{v.name}</div>
                      <div className="flex items-center gap-2">
                        <input 
                          className="bg-transparent text-lg font-bold w-full outline-none border-b border-[#F5A623]/20 focus:border-[#F5A623] transition-all font-mono"
                          value={v.value}
                          type="number"
                          onChange={(e) => {
                            const newVitals = [...editingRecord.vitals];
                            newVitals[i].value = parseFloat(e.target.value);
                            setEditingRecord({ ...editingRecord, vitals: newVitals });
                          }}
                        />
                        <span className="text-[10px] text-gray-600 uppercase font-mono">{v.unit}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <h5 className="text-[10px] uppercase font-bold text-gray-500 tracking-widest border-b border-white/5 pb-2 mt-8">Symptoms State (Tri-State)</h5>
                <div className="flex flex-wrap gap-2">
                  {editingRecord.symptoms.map((s, i) => (
                    <button 
                      key={i}
                      onClick={() => {
                        const newSymptoms = [...editingRecord.symptoms];
                        const states = ['True', 'False', 'Unknown'];
                        const nextState = states[(states.indexOf(s.status) + 1) % 3];
                        newSymptoms[i].status = nextState;
                        setEditingRecord({ ...editingRecord, symptoms: newSymptoms });
                      }}
                      className={`px-3 py-2 rounded-xl text-xs border transition-all ${
                        s.status === 'True' ? 'bg-indigo-500/20 border-indigo-400 text-indigo-300' :
                        s.status === 'False' ? 'bg-red-500/10 border-red-400/30 text-red-300' :
                        'bg-white/5 border-white/10 text-gray-500'
                      }`}
                    >
                      {s.name}: <span className="font-bold">{s.status}</span>
                    </button>
                  ))}
                </div>

                <h5 className="text-[10px] uppercase font-bold text-gray-500 tracking-widest border-b border-white/5 pb-2 mt-8">Lifestyle Suspicions</h5>
                <div className="flex flex-wrap gap-2">
                  {(editingRecord.lifestyle_factors || []).map((l, i) => (
                    <button 
                      key={i}
                      onClick={() => {
                        const newFactors = [...(editingRecord.lifestyle_factors || [])];
                        const states = ['True', 'False', 'Unknown'];
                        const nextState = states[(states.indexOf(l.status) + 1) % 3];
                        newFactors[i].status = nextState;
                        setEditingRecord({ ...editingRecord, lifestyle_factors: newFactors });
                      }}
                      className={`px-3 py-2 rounded-xl text-xs border transition-all ${
                        l.status === 'True' ? 'bg-amber-500/20 border-amber-400 text-amber-300' :
                        l.status === 'False' ? 'bg-green-500/10 border-green-400/30 text-green-300' :
                        'bg-white/5 border-white/10 text-gray-500'
                      }`}
                    >
                      {l.name}: <span className="font-bold">{l.status}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-4 pt-6 border-t border-white/5">
              <button 
                onClick={() => setEditingRecord(null)}
                className="px-8 py-3 rounded-full text-xs font-bold uppercase tracking-widest border border-white/10 hover:bg-white/5 transition-all text-gray-400"
              >
                Discard Edits
              </button>
              <button 
                onClick={handleUpdateClick}
                className="px-8 py-3 rounded-full text-xs font-bold uppercase tracking-widest bg-gradient-to-r from-[#F5A623] to-[#E09612] text-black hover:scale-[1.02] active:scale-[0.98] transition-all shadow-[0_0_20px_rgba(245,166,35,0.3)]"
              >
                Validate & Commit to EHRS
              </button>
            </div>
          </div>
        </div>
      )}
      
      <div className="p-3 bg-white/2 text-[10px] text-gray-600 flex gap-4">
         <span>TOTAL RECORDS: {data.length}</span>
         <span>•</span>
         <span>SOURCE: POSTGRES EHRS</span>
         <span className="ml-auto italic">Authorized Terminal: Aushasda Precision Engineering</span>
      </div>
    </div>
  );
};

export default EHRTabularView;
