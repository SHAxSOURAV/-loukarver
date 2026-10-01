import React, { useEffect, useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Select } from "antd";
import { Navigate } from "../../Navigate";
import { useSelector } from "react-redux";

const Analytics = () => {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(String(currentYear));
  const [years, setYears] = useState([]);
  const [feature, setFeature] = useState("CheckIn");
  const [monthlyData, setMonthlyData] = useState([]);
  const [maxUsers, setMaxUsers] = useState(0);
  const { token } = useSelector((state) => state.logInUser);

  useEffect(() => {
    const startYear = 2024;
    const yearsArray = Array.from(
      { length: currentYear - startYear + 1 },
      (_, index) => String(startYear + index)
    );
    setYears(yearsArray);
  }, [currentYear]);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/analytics?year=${year}&feature=${feature}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setMonthlyData(data);
          
          // Calculate max users to dynamically set Y-axis height
          const maxVal = Math.max(...data.flatMap(d => [d.Men, d.Women]), 0);
          setMaxUsers(maxVal);
        }
      } catch (error) {
        console.error("Failed to fetch analytics", error);
      }
    };
    
    if (token) fetchAnalytics();
  }, [year, feature, token]);

  return (
    <div className="bg-white p-3 h-[87vh] overflow-auto">
      <div className="flex justify-between mb-4">
         <Navigate title={"Analytics"} />
        <div className="flex gap-4">
          <Select
            value={feature}
            onChange={(val) => setFeature(val)}
            options={[
              { value: "CheckIn", label: "Check In" },
              { value: "DatePlanning", label: "Date Planning" },
              { value: "Appreciation", label: "Appreciation" },
              { value: "FutureGoal", label: "Future Goal" },
              { value: "MapFeature", label: "Map Feature" },
            ]}
            style={{ maxWidth: "300px", height: "40px" }}
          />
          <Select
            placeholder="Select Year"
            options={years.map((y) => ({ value: y, label: y }))}
            style={{ maxWidth: "120px", height: "40px" }}
            value={year}
            onChange={(val) => setYear(val)}
          />
        </div>
      </div>

      <ResponsiveContainer width="100%" height={600}>
        <AreaChart
          data={monthlyData}
          margin={{ top: 20, right: 20, left: 0, bottom: 10 }}
        >
          <defs>
            <linearGradient id="colorMen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1890ff" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#1890ff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorWomen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff7f0e" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ff7f0e" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="name"
            stroke="#333"
            tick={{ fontSize: 12, fontWeight: 500 }}
          />
          <YAxis
            stroke="#333"
            domain={[0, maxUsers + 50]}
            tick={{ fontSize: 12, fontWeight: 500 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #ddd",
              borderRadius: "8px",
              padding: "8px",
            }}
          />
          <Legend wrapperStyle={{ fontSize: "13px", fontWeight: "bold" }} />
          <Area
            type="monotone"
            dataKey="Men"
            stroke="#1890ff"
            fillOpacity={1}
            fill="url(#colorMen)"
          />
          <Area
            type="monotone"
            dataKey="Women"
            stroke="#ff7f0e"
            fillOpacity={1}
            fill="url(#colorWomen)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Analytics;