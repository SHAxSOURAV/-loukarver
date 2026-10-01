import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import React, { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { Select } from "antd";

const UserGrowthChart = () => {
  const { token } = useSelector((state) => state.logInUser);
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [years, setYears] = useState([]);
  const [monthlyData, setMonthlyData] = useState([]);
  const [maxUsers, setMaxUsers] = useState(0);

  useEffect(() => {
    const startYear = 2024;
    const yearsArray = Array.from(
      { length: currentYear - startYear + 1 },
      (_, index) => startYear + index,
    );
    setYears(yearsArray);
  }, [currentYear]);

  useEffect(() => {
    const fetchGrowth = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/stats/user-growth?year=${year}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setMonthlyData(data);
          const maxVal = Math.max(...data.map(d => d.totalUser), 0);
          setMaxUsers(maxVal + 4);
        }
      } catch (error) {
        console.error("Failed to fetch user growth", error);
      }
    };
    if (token) fetchGrowth();
  }, [year, token]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
      }}
    >
      <div className="flex justify-between items-center">
        <h3
          style={{
            textAlign: "left",
            marginBottom: "15px",
            color: "#333",
            fontWeight: "bold",
            fontSize: "18px",
          }}
        >
          📈 User Growth
        </h3>
        <Select
          className="min-w-32"
          value={year}
          placeholder="Select year"
          onChange={setYear}
          style={{
            marginBottom: "15px",
            width: "150px",
            fontWeight: "500",
          }}
          options={years.map((item) => ({ value: item, label: item }))}
        />
      </div>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart
          data={monthlyData}
          margin={{ top: 20, right: 20, left: 0, bottom: 10 }}
        >
          <defs>
            <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="url(#colorValue)" stopOpacity={1} />
              <stop offset="95%" stopColor="#14803c" stopOpacity={1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#edc4c500" />
          <XAxis
            dataKey="name"
            stroke="#333"
            tick={{ fontSize: 12, fontWeight: 500 }}
          />
          <YAxis
            stroke="#333"
            domain={[0, maxUsers]}
            tick={{ fontSize: 12, fontWeight: 500 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #ddd",
              borderRadius: "8px",
              padding: "8px",
            }}
            cursor={{ fill: "#edc4c52d" }}
          />
          <Legend wrapperStyle={{ fontSize: "13px", fontWeight: "bold" }} />
          <Bar
            dataKey="totalUser"
            fill="url(#colorValue)"
            barSize={45}
            radius={[10, 10, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default UserGrowthChart;
