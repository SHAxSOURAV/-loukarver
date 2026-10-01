import { Select } from "antd";
import React, { useState, useEffect } from "react";
import { useSelector } from "react-redux";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

const BookingGrowth = () => {
  const { token } = useSelector((state) => state.logInUser);
  const [year, setYear] = useState("2024");
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    const fetchEarnings = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/stats/earnings?year=${year}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setChartData(data);
        }
      } catch (error) {
        console.error("Failed to fetch earnings", error);
      }
    };
    if (token) fetchEarnings();
  }, [year, token]);

  const handleYearChange = (value) => {
    setYear(value);
  };

  const items = [
    { value: "2024", label: "2024" },
    { value: "2023", label: "2023" },
    { value: "2022", label: "2022" },
  ];

  return (
    <div className="">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <p className="text-xl font-semibold text-gray-800">
          Total Earnings
        </p>

        <Select
          defaultValue="2024"
          onChange={handleYearChange}
          options={items}
          className="w-32"
        />
      </div>

      {/* Chart */}
      <div className="h-96">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#B7835E" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#B7835E" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#edc4c500" />
            <XAxis dataKey="month" stroke="#6b7280"  tick={{ fontSize: 12, fontWeight: 500 }}/>
            <YAxis stroke="#6b7280"  tick={{ fontSize: 12, fontWeight: 500 }}/>
            <Tooltip
              contentStyle={{ backgroundColor: "#fff", borderRadius: "8px" }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="#B7835E"
              fillOpacity={1}
              fill="url(#colorValue)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default BookingGrowth;
