import React from 'react';

interface Vital {
  name: string;
  value: number;
  unit: string;
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
}

interface Props {
  data: EHRRecord[];
}

const EHRDataTable: React.FC<Props> = ({ data }) => {
  return (
    <div className="p-6 space-y-8 fade-in-up">
      <h2 className="text-3xl font-bold text-[#F5A623] mb-6">Structured Clinical Intelligence</h2>
      
      {data.length === 0 ? (
        <div className="glass-panel p-10 text-center text-gray-400">
          No structured EHR data available. Extract data by processing medical documents.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8">
          {data.map((record, index) => (
            <div key={index} className="glass-panel p-8 space-y-6">
              <div className="flex justify-between items-start border-b border-white/10 pb-4">
                <div>
                  <div className="text-xs uppercase tracking-widest text-[#F5A623] mb-1">Case Identifier</div>
                  <div className="text-2xl font-semibold">{record.case_id}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs uppercase tracking-widest text-gray-500 mb-1">Visit Date</div>
                  <div className="text-lg font-medium">{record.visit_date}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                <div>
                  <div className="text-xs text-gray-500 uppercase mb-1">Age Group</div>
                  <div className="font-medium">{record.age_group}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase mb-1">Sex</div>
                  <div className="font-medium">{record.sex}</div>
                </div>
                <div className="col-span-2">
                  <div className="text-xs text-gray-500 uppercase mb-1">Primary Condition</div>
                  <div className="font-medium text-[#F5A623]">{record.condition_name}</div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-sm uppercase tracking-wider font-bold text-gray-300">Clinical Vitals</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {record.vitals.map((v, i) => (
                    <div key={i} className="bg-black/20 rounded-xl p-4 border border-white/5">
                      <div className="text-[10px] text-gray-500 uppercase mb-1">{v.name}</div>
                      <div className="flex items-baseline gap-1">
                        <span className="text-xl font-bold">{v.value}</span>
                        <span className="text-xs text-gray-500">{v.unit}</span>
                      </div>
                      <div className={`text-[10px] mt-2 inline-block px-2 py-0.5 rounded-full ${
                        v.status === 'Critical' ? 'bg-red-500/20 text-red-400' :
                        v.status === 'Elevated' ? 'bg-orange-500/20 text-orange-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>
                        {v.status}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h3 className="text-sm uppercase tracking-wider font-bold text-gray-300">Symptom Assessment</h3>
                  <div className="flex flex-wrap gap-2">
                    {record.symptoms.map((s, i) => (
                      <span key={i} className={`px-3 py-1 rounded-lg text-xs font-medium border ${
                        s.status === 'True' ? 'bg-indigo-500/10 border-indigo-400/30 text-indigo-300' : 'bg-gray-500/5 border-white/5 text-gray-500'
                      }`}>
                        {s.name}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="space-y-4">
                  <h3 className="text-sm uppercase tracking-wider font-bold text-gray-300">Chief Complaint</h3>
                  <p className="text-sm text-gray-400 leading-relaxed italic">
                    "{record.chief_complaint}"
                  </p>
                  {record.red_flag_any && (
                    <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                      <div className="text-xs font-bold text-red-400 uppercase mb-2">Red Flag Warnings Detected</div>
                      <div className="flex flex-wrap gap-1">
                        {record.red_flag_details.map((d, i) => (
                          <span key={i} className="text-xs text-red-300">• {d}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EHRDataTable;
