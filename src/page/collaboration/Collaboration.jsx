import React, { useState, useEffect } from "react";
import { Input, Modal, Select, Table, message } from "antd";
import { HiOutlineUserGroup } from "react-icons/hi2";
import { LuEye } from "react-icons/lu";
import { MdBlockFlipped, MdDelete } from "react-icons/md";
import { AiOutlineHeart } from "react-icons/ai";
import { SearchOutlined } from "@ant-design/icons";
import { useSelector } from "react-redux";
import { Navigate } from "../../Navigate";

const { confirm } = Modal;

const Collaboration = () => {
  const { token } = useSelector((state) => state.logInUser);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // States for API data
  const [collaborators, setCollaborators] = useState([]);
  const [totalCouples, setTotalCouples] = useState(0);
  const [activeCouples, setActiveCouples] = useState(0);

  // Filter states
  const [statusFilter, setStatusFilter] = useState("Active");
  const [subscriptionFilter, setSubscriptionFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchCollaborations();
  }, [statusFilter, searchQuery]);

  const fetchCollaborations = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/collaborations?status=${statusFilter}&search=${searchQuery}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setTotalCouples(data.total_couples);
        setActiveCouples(data.active_couples);
        setCollaborators(data.collaborators);
      }
    } catch (error) {
      console.error("Failed to fetch collaborations", error);
    }
  };

  const handleStatusUpdate = async (userId, payload, successMessage) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/users/${userId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        message.success(successMessage);
        fetchCollaborations(); // Refresh list
        setIsModalOpen(false);
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to update user");
      }
    } catch (error) {
      message.error("An error occurred");
    }
  };

  const showModal = (record) => {
    setSelectedUser(record);
    setIsModalOpen(true);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setSelectedUser(null);
  };

  const confirmBlock = (user) => {
    const isBlocked = user.is_blocked;
    confirm({
      title: `Are you sure you want to ${isBlocked ? "unblock" : "block"} this user?`,
      content: `User: ${user.name || user.email}`,
      okText: "Yes",
      cancelText: "No",
      onOk() {
        handleStatusUpdate(user.id, { is_blocked: !isBlocked }, `User successfully ${isBlocked ? "unblocked" : "blocked"}`);
      }
    });
  };

  const confirmDelete = (user) => {
    confirm({
      title: "Are you sure you want to delete this user?",
      content: `User: ${user.name || user.email}. This action will soft-delete the user.`,
      okText: "Yes, Delete",
      okType: "danger",
      cancelText: "No",
      onOk() {
        handleStatusUpdate(user.id, { is_deleted: true }, "User successfully deleted");
      }
    });
  };

  // Filter subscription on frontend since it's simple
  const displayedCollaborators = subscriptionFilter === "All" 
    ? collaborators 
    : collaborators.filter(c => c.subscription === subscriptionFilter);

  // Table Columns
  const columns = [
    {
      title: "User",
      key: "name",
      render: (_, record) => (
        <div className="flex items-center gap-3">
          <img
            src={record.image}
            className="w-10 h-10 object-cover rounded-full border"
            alt=""
          />
          <span className="font-medium">{record.name || record.email}</span>
        </div>
      ),
    },
    {
      title: "Connected Date",
      dataIndex: "connectedDate",
    },
    {
      title: "Duration",
      dataIndex: "duration",
    },
    {
      title: "Subscription",
      dataIndex: "subscription",
      render: (text) => (
        <span className="px-2 py-1 bg-blue-100 text-blue-600 rounded-md text-xs">
          {text}
        </span>
      ),
    },
    {
      title: "Relationship",
      dataIndex: "relationship",
      render: (text) => (
        <span className="px-2 py-1 bg-pink-100 text-pink-600 rounded-md text-xs">
          {text}
        </span>
      ),
    },
    {
      title: "Actions",
      key: "action",
      render: (_, record) => (
        <div className="flex gap-2">
          <button onClick={() => showModal(record)}>
            <LuEye className="text-xl text-blue-600" />
          </button>

          <button
            onClick={() => confirmBlock(record)}
            className="bg-red-500 text-white p-1 rounded"
          >
            <MdBlockFlipped />
          </button>

          <button
            onClick={() => confirmDelete(record)}
            className="bg-gray-800 text-white p-1 rounded"
          >
            <MdDelete />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="bg-white p-3 h-[87vh] overflow-auto">
      <Navigate title={"Collaboration Management"} />
      <div className="grid grid-cols-2 gap-4">
        {/* Total Couples */}
        <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
          <div className="bg-pink-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
            <HiOutlineUserGroup className="text-pink-600" />
          </div>
          <div>
            <h1 className="font-semibold text-2xl">{totalCouples.toLocaleString()}</h1>
            <h1 className="text-zinc-500">Total Couples</h1>
          </div>
        </div>

        {/* Active Couples */}
        <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
          <div className="bg-green-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
            <AiOutlineHeart className="text-green-600" />
          </div>
          <div>
            <h1 className="font-semibold text-2xl">{activeCouples.toLocaleString()}</h1>
            <h1 className="text-zinc-500">Active Couples</h1>
          </div>
        </div>
      </div>

      <div className="flex gap-4 justify-end mt-4 mb-2">
        <Select
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: "Active", label: "Active" },
            { value: "Blocked", label: "Blocked" },
            { value: "All", label: "All" }
          ]}
          style={{ maxWidth: "300px", minWidth: "120px", height: "40px" }}
        />

        <Select
          value={subscriptionFilter}
          onChange={setSubscriptionFilter}
          options={[
            { value: "All", label: "All Plans" },
            { value: "Free", label: "Free" },
            { value: "Individual Plan", label: "Individual Plan" },
            { value: "Couple Plan", label: "Couple Plan" },
          ]}
          style={{ maxWidth: "300px", minWidth: "150px", height: "40px" }}
        />

        <Input
          placeholder="Search by name..."
          prefix={<SearchOutlined />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ maxWidth: "300px", height: "40px" }}
        />
        
        <div>
          <button className="bg-[#C09B7A80] py-2 text-[#8B4513] px-5 rounded cursor-not-allowed opacity-70">
            Export
          </button>
        </div>
      </div>

      <Table
        dataSource={displayedCollaborators}
        columns={columns}
        pagination={false}
        scroll={{ x: "max-content" }}
        rowKey="id"
      />

      {/* Modal */}
      <Modal open={isModalOpen} footer={null} onCancel={handleCancel} centered>
        {selectedUser && (
          <div className="p-5 text-center">
            {/* Profile */}
            <div className="flex flex-col items-center">
              <img
                src={selectedUser.image}
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-200 mb-3"
                alt=""
              />
              <h2 className="text-xl font-bold">{selectedUser.name || "Unknown"}</h2>
              <p className="text-gray-500 text-sm">{selectedUser.email}</p>
            </div>

            {/* Info */}
            <div className="mt-6 space-y-3 text-left">
              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Connected Date</span>
                <span className="font-medium">
                  {selectedUser.connectedDate}
                </span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Duration</span>
                <span className="font-medium">{selectedUser.duration}</span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Subscription</span>
                <span className="text-blue-600 font-medium">
                  {selectedUser.subscription}
                </span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Relationship</span>
                <span className="text-pink-600 font-medium">
                  {selectedUser.relationship}
                </span>
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => confirmBlock(selectedUser)}
                className="flex-1 bg-red-500 text-white py-2 rounded-lg"
              >
                {selectedUser.is_blocked ? "Unblock" : "Block"}
              </button>
              <button
                onClick={() => confirmDelete(selectedUser)}
                className="flex-1 bg-gray-800 text-white py-2 rounded-lg"
              >
                Delete
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Collaboration;
