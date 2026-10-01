import React, { useState, useEffect } from "react";
import { Table, Modal, message } from "antd";
import { LuEye } from "react-icons/lu";
import { MdBlockFlipped, MdDelete } from "react-icons/md";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

const { confirm } = Modal;

const ShopRegister = () => {
  const { token } = useSelector((state) => state.logInUser);
  const navigate = useNavigate();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [users, setUsers] = useState([]);

  const fetchCollaborations = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/recent-collaborations`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (error) {
      console.error("Failed to fetch collaborations", error);
    }
  };

  useEffect(() => {
    if (token) fetchCollaborations();
  }, [token]);

  const showModal = (record) => {
    setSelectedUser(record);
    setIsModalOpen(true);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setSelectedUser(null);
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
        setIsModalOpen(false); // Close modal if open
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to update user");
      }
    } catch (error) {
      message.error("An error occurred");
    }
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

  const columns = [
    {
      title: "User",
      key: "name",
      render: (_, record) => (
        <div className="flex items-center gap-3">
          <img
            src={record.profile_photo_url || `https://ui-avatars.com/api/?name=${record.name || record.email}`}
            className="w-10 h-10 object-cover rounded-full border"
            alt=""
          />
          <span className="font-medium">{record.name || "Unknown"}</span>
        </div>
      ),
    },
    {
      title: "Connected Date",
      key: "connectedDate",
      render: (_, record) => {
        // Since we don't store exactly when partner connected, we fallback to account creation
        // or a default value, here we can just show join duration we calculated
        return <span>{record.join_duration} ago</span>;
      }
    },
    {
      title: "Duration",
      dataIndex: "join_duration",
      key: "duration",
    },
    {
      title: "Subscription",
      key: "subscription",
      render: () => (
        <span className="px-2 py-1 bg-blue-100 text-blue-600 rounded-md text-xs">
          Free
        </span>
      ),
    },
    {
      title: "Relationship",
      key: "relationship",
      render: (_, record) => (
        <span className="px-2 py-1 bg-pink-100 text-pink-600 rounded-md text-xs">
          {record.is_aligned ? "Aligned" : (record.partner ? "Connected" : "Single")}
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
            className={`${record.is_blocked ? "bg-orange-500" : "bg-red-500"} text-white p-1 rounded`}
            title={record.is_blocked ? "Unblock User" : "Block User"}
          >
            <MdBlockFlipped />
          </button>

          <button
            onClick={() => confirmDelete(record)}
            className="bg-gray-800 text-white p-1 rounded"
            title="Delete User"
          >
            <MdDelete />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="">
       <div className="flex mb-3 justify-between">
        <p className="text-xl font-semibold text-gray-800">
          Recent Collaboration
        </p>
        <button 
          className="text-[#B7835E]"
          onClick={() => navigate("/dashboard/UserManagement")}
        >
          View All
        </button>
       </div>
      <Table
        dataSource={users}
        columns={columns}
        pagination={false}
        rowKey="id"
        scroll={{ x: "max-content" }}
      />

      <Modal
        open={isModalOpen}
        footer={null}
        onCancel={handleCancel}
        centered
      >
        {selectedUser && (
          <div className="p-5 text-center">
            <div className="flex flex-col items-center">
              <img
                src={selectedUser.profile_photo_url || `https://ui-avatars.com/api/?name=${selectedUser.name || selectedUser.email}`}
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-200 mb-3"
                alt=""
              />
              <h2 className="text-xl font-bold">{selectedUser.name || "Unknown"}</h2>
              <p className="text-gray-500 text-sm">
                {selectedUser.email}
              </p>
            </div>

            <div className="mt-6 space-y-3 text-left">
              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Connected Date</span>
                <span className="font-medium">
                  {selectedUser.join_duration} ago
                </span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Duration</span>
                <span className="font-medium">
                  {selectedUser.join_duration}
                </span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Subscription</span>
                <span className="text-blue-600 font-medium">
                  Free
                </span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span className="text-gray-500">Relationship</span>
                <span className="text-pink-600 font-medium">
                  {selectedUser.is_aligned ? "Aligned" : (selectedUser.partner ? "Connected" : "Single")}
                </span>
              </div>
            </div>

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

export default ShopRegister;