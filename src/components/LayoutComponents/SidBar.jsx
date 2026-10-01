import dashboard from "../../assets/routerImg/dashboard.png";
import categorie from "../../assets/routerImg/categorie.png";
import create from "../../assets/routerImg/create.png";
import settings from "../../assets/routerImg/settings.png";
import subscription from "../../assets/routerImg/subscription.png";
import user from "../../assets/routerImg/user.png";
import logo from "../../assets/header/logo.png";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { FaChevronRight, FaHome } from "react-icons/fa";
import { IoIosLogIn } from "react-icons/io";
import { logout } from "../../page/redux/features/auth/authSlice";
import { useDispatch } from "react-redux";
import { FiUser } from "react-icons/fi";
import { IoSettingsOutline } from "react-icons/io5";
import { TbCategory2 } from "react-icons/tb";


const items = [
  {
    key: "dashboard",
    label: "Dashboard",
    icon: <FaHome />,
    link: "/",
  },
  {
    key: "userManagement",
    label: "User Management",
    icon: <FiUser />,
    link: "/dashboard/UserManagement",
  },

     {
    key: "analytics",
    label: "Analytics",
    icon: <FiUser />,
    link: "/dashboard/analytics",
  },
    {
    key: "collaboration",
    label: "Collaboration",
    icon: <FiUser />,
    link: "/dashboard/collaboration",
  },
   {
    key: "transaction",
    label: "Transaction",
    icon: <FiUser />,
    link: "/dashboard/transaction",
  },
   {
    key: "report",
    label: "Report",
    icon: <FiUser />,
    link: "/dashboard/report",
  },
  
 
  {
    key: "settings",
    label: "Settings",
    icon:<IoSettingsOutline />,
    link: "/dashboard/Settings/profile",
    children: [
      {
        key: "profile",
        label: "Profile",
        link: "/dashboard/Settings/profile",
      },
      {
        key: "terms",
        label: "Terms & Condition",
        link: "/dashboard/Settings/Terms&Condition",
      },
      {
        key: "privacy",
        label: "Privacy Policy",
        link: "/dashboard/Settings/PrivacyPolicy",
      },
    
    ],
  },
];

const SidBar = () => {
  const [selectedKey, setSelectedKey] = useState("dashboard");
  const [expandedKeys, setExpandedKeys] = useState([]);
  const location = useLocation();
  const navigate = useNavigate();
  const contentRef = useRef({});
  const dispatch = useDispatch();

  useEffect(() => {
    const currentPath = location.pathname;

    let activeParent = null;

    items.forEach((item) => {
      if (item.link === currentPath) {
        activeParent = item;
      } else if (
        item.children &&
        item.children.some((child) => child.link === currentPath)
      ) {
        activeParent = item;
      }
    });

    if (activeParent) {
      setSelectedKey(
        activeParent.children
          ? activeParent.children.find((child) => child.link === currentPath)
              ?.key || activeParent.key
          : activeParent.key
      );

      if (activeParent.children && !expandedKeys.includes(activeParent.key)) {
        setExpandedKeys([...expandedKeys, activeParent.key]);
      }
    }
  }, [location]);

  const onParentClick = (key) => {
    setExpandedKeys((prev) =>
      prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key]
    );
  };

  // Logout Function
  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  return (
    <div className="custom-sidebar h-[100vh] bg-[#C09B7A] text-white">
      <div className="custom-sidebar-logo flex justify-center py-6">
        <img src={logo} alt="Logo" className="w-[120px]" />
      </div>
      <div className="menu-items">
       {items.map((item) => (
          <div key={item.key}>
            <Link
              to={item.link}
              className={`my-2 mx-2 rounded py-[10px] px-4 flex items-center cursor-pointer ${
                selectedKey === item.key
                  ? "bg-white   text-black"
                  : "hover:bg-gradient-to-r hover:from-[#868686]"
              }`}
              onClick={(e) => {
                if (item.children) {
                  e.preventDefault();
                  onParentClick(item.key);
                } else {
                  setSelectedKey(item.key);
                }
              }}
            >
              <span className="w-5 mr-2 text-lg">{item.icon}</span>
              <span className="w-full">{item.label}</span>

              {item.children && (
                <FaChevronRight
                  className={`ml-auto text-[10px] transition-transform duration-300 ${
                    expandedKeys.includes(item.key) ? "rotate-90" : ""
                  }`}
                />
              )}
            </Link>

            {item.children && (
              <div
                className="ml-6 mx-2 overflow-hidden transition-all duration-300"
                style={{
                  maxHeight: expandedKeys.includes(item.key)
                    ? `${contentRef.current[item.key]?.scrollHeight}px`
                    : "0",
                }}
                ref={(el) => (contentRef.current[item.key] = el)}
              >
                {item.children.map((child) => (
                  <Link
                    key={child.key}
                    to={child.link}
                    className={`p-2 flex items-center ${
                      selectedKey === child.key
                        ? "bg-white text-black rounded"
                        : "hover:bg-gradient-to-r hover:from-[#868686] rounded"
                    }`}
                    onClick={() => setSelectedKey(child.key)}
                  >
                    {child.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Logout Button */}
      <div className="mx-4 ">
        <div className=" border-white rounded w-full p-3 border mt-4">
        <button
          onClick={handleLogout}
          className=" flex items-center text-[white] text-start rounded-md  "
        >
          <span className="text-2xl">
            <IoIosLogIn />
          </span>
          <span className="ml-3">Log Out</span>
        </button>
      </div>
      </div>
    </div>
  );
};

export default SidBar;
