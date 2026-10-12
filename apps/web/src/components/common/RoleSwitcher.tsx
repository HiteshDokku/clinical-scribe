import React, { useEffect, useState } from 'react';

export const RoleSwitcher = () => {
  const [role, setRole] = useState('clinician');

  useEffect(() => {
    const saved = localStorage.getItem('demo_role');
    if (saved) {
      setRole(saved);
    } else {
      localStorage.setItem('demo_role', 'clinician');
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newRole = e.target.value;
    setRole(newRole);
    localStorage.setItem('demo_role', newRole);
    window.location.reload();
  };

  return (
    <div className="fixed bottom-6 right-6 z-[9999] bg-white/[0.05] backdrop-blur-md border border-white/[0.1] rounded-full p-1.5 shadow-2xl flex items-center gap-2">
      <label className="text-xs font-medium text-gray-400 pl-3">Role:</label>
      <select 
        value={role} 
        onChange={handleChange} 
        className="bg-clinical-900/50 text-clinical-100 text-sm border-none rounded-full px-4 py-1.5 focus:ring-1 focus:ring-clinical-500/50 outline-none cursor-pointer appearance-none pr-8 relative hover:bg-clinical-800/50 transition-colors"
        style={{ backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%239CA3AF%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.7rem top 50%', backgroundSize: '0.65rem auto' }}
      >
        <option value="clinician">Clinician</option>
        <option value="admin">Admin</option>
      </select>
    </div>
  );
};
