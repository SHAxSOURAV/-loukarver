import { RiUserForbidLine } from "react-icons/ri";
import ActivityStatisticsChart from "./ActivityStatisticsChart";
import BookingGrowth from "./BookingGrowth";
import ShopRegistration from "./ShopRegister";
import UserGrowthChart from "./UserGrowthChart";
import { HiOutlineUserGroup } from "react-icons/hi2";
import { VscNote } from "react-icons/vsc";
import { PiMoneyLight } from "react-icons/pi";
import { AiOutlineHeart } from "react-icons/ai";
import { useState, useEffect } from "react";
import { useSelector } from "react-redux";

const Dashboard = () => {
  const { token } = useSelector((state) => state.logInUser);
  const [stats, setStats] = useState({
    total_users: 0,
    active_relationships: 0,
    total_earning: NaN,
    active_subscriptions: NaN
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/stats`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (error) {
        console.error("Failed to fetch dashboard stats", error);
      }
    };
    if (token) fetchStats();
  }, [token]);

  return (
    <div className=" ">
      <div className="grid grid-cols-4 gap-4">
        <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
          <div className="bg-red-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
            <HiOutlineUserGroup className="text-red-500" />
          </div>
          <div>
            <h1 className="font-semibold text-2xl">{stats.total_users.toLocaleString()}</h1>
            <h1 className="text-zinc-500"> Total User</h1>
          </div>
        </div>
        <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
          <div className="bg-sky-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
           <AiOutlineHeart className="text-sky-600" />
          </div>
          <div>
            <h1 className="font-semibold text-2xl">{stats.active_relationships.toLocaleString()}</h1>
            <h1 className="text-zinc-500"> Active Relationships</h1>
          </div>
        </div>
        <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
          <div className="bg-green-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
             <PiMoneyLight className="text-green-500" />
          </div>
          <div>
            <h1 className="font-semibold text-2xl">{Number.isNaN(stats.total_earning) ? "NaN" : stats.total_earning}</h1>
            <h1 className="text-zinc-500"> Total Earning</h1>
          </div>
        </div>
        <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
          <div className="bg-purple-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
           <VscNote className="text-purple-500" />
          </div>
          <div>
            <h1 className="font-semibold text-2xl">{Number.isNaN(stats.active_subscriptions) ? "NaN" : stats.active_subscriptions}</h1>
            <h1 className="text-zinc-500"> Active Subscriptions</h1>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 mt-4 ">
        <div className="w-full h-full bg-white p-4 rounded shadow">
          <UserGrowthChart />
        </div>
        <div className=" bg-white p-4 rounded shadow ">
          {/* <ActivityStatisticsChart /> */}
          <BookingGrowth></BookingGrowth>
        </div>
      </div>

      <div className="w-full bg-white p-4 rounded shadow mt-4">
        <ShopRegistration></ShopRegistration>
      </div>
    </div>
  );
};

export default Dashboard;
