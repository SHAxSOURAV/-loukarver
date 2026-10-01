import { Outlet } from "react-router-dom";
import Header from "../../components/LayoutComponents/Header";
import SidBar from "../../components/LayoutComponents/SidBar";

const DashboardLayout = () => {
  return (
    <div className="lg:flex ">
      <div className="lg:w-[260px] bg-[#FEFEFE] overflow-auto lg:fixed lg:top-0 lg:left-0 lg:bottom-0 hidden lg:block no-scrollbar">
        <SidBar />
      </div>

      <div className=" lg:flex-1 lg:ml-[260px]">
        <Header />
        <div className="p-3 bg-slate-50">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default DashboardLayout;
