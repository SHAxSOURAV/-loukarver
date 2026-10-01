import React, { useState, useEffect } from "react";
import { Input, Modal, Pagination, Select, Table, message, Dropdown, Menu } from "antd";
import { MdBlockFlipped } from "react-icons/md";
import { SearchOutlined, MoreOutlined } from "@ant-design/icons";
import { LuEye, LuEyeOff } from "react-icons/lu";
import { RiDeleteBin6Line } from "react-icons/ri";
import { useSelector } from "react-redux";
import { Navigate } from "../../Navigate";

const { confirm } = Modal;

const UserManagement = () => {
  const { token } = useSelector((state) => state.logInUser);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;
  
  const [users, setUsers] = useState([]);
  const [statusFilter, setStatusFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal state
  const [isModalOpen2, setIsModalOpen2] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, [statusFilter]);

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/users?status_filter=${statusFilter}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (error) {
      console.error("Failed to fetch users", error);
    }
  };

  const showModal2 = (record) => {
    setSelectedUser(record);
    setIsModalOpen2(true);
  };

  const handleCancel2 = () => {
    setIsModalOpen2(false);
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
        fetchUsers(); // Refresh list
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

  const toggleHide = (user) => {
    const isHidden = user.is_hidden;
    handleStatusUpdate(user.id, { is_hidden: !isHidden }, `User successfully ${isHidden ? "unhidden" : "hidden"}`);
  };

  // ✅ Columns
  const columns = [
    {
      title: "User",
      key: "user",
      render: (_, record) => (
        <div className="flex items-center gap-3">
          <img
            src={record.profile_photo_url || `https://ui-avatars.com/api/?name=${record.name || record.email}`}
            className="w-10 h-10 object-cover rounded-full"
            alt=""
          />
          <div>
            <p className="font-medium">{record.name || "Unknown"}</p>
            <p className="text-xs text-gray-500">{record.email}</p>
          </div>
        </div>
      ),
    },
    {
      title: "Partner Connection",
      key: "partnerConnection",
      render: (_, record) => (
        <span>{record.partner ? "Connected" : "None"}</span>
      )
    },
    {
      title: "Aligned",
      key: "subscription",
      render: (_, record) => (
        <span className="px-2 py-1 bg-blue-100 text-blue-600 rounded text-xs">
          {record.is_aligned ? "Aligned" : "Not Aligned"}
        </span>
      ),
    },
    {
      title: "Status",
      key: "status",
      render: (_, record) => {
        if (record.is_deleted) return <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-600">Deleted</span>;
        if (record.is_blocked) return <span className="px-2 py-1 rounded text-xs bg-red-100 text-red-600">Blocked</span>;
        if (record.is_hidden) return <span className="px-2 py-1 rounded text-xs bg-gray-100 text-gray-600">Hidden</span>;
        return <span className="px-2 py-1 rounded text-xs bg-green-100 text-green-600">Active</span>;
      },
    },
    {
      title: "Actions",
      key: "action",
      render: (_, record) => {
        const menu = (
          <Menu>
            <Menu.Item key="1" onClick={() => showModal2(record)} icon={<LuEye />}>
              View Details
            </Menu.Item>
            {!record.is_deleted && (
              <>
                <Menu.Item key="2" onClick={() => confirmBlock(record)} icon={<MdBlockFlipped />}>
                  {record.is_blocked ? "Unblock" : "Block"}
                </Menu.Item>
                <Menu.Item key="3" onClick={() => toggleHide(record)} icon={record.is_hidden ? <LuEye /> : <LuEyeOff />}>
                  {record.is_hidden ? "Unhide" : "Hide"}
                </Menu.Item>
                <Menu.Item key="4" danger onClick={() => confirmDelete(record)} icon={<RiDeleteBin6Line />}>
                  Delete
                </Menu.Item>
              </>
            )}
          </Menu>
        );

        return (
          <Dropdown overlay={menu} trigger={['click']}>
            <button className="text-xl px-3 py-1 bg-gray-100 rounded-md hover:bg-gray-200">
              <MoreOutlined />
            </button>
          </Dropdown>
        );
      },
    },
  ];

  // Pagination & Search
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const filteredUsers = users.filter(user => 
    (user.name?.toLowerCase() || "").includes(searchQuery.toLowerCase()) ||
    (user.email?.toLowerCase() || "").includes(searchQuery.toLowerCase())
  );

  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;
  const paginatedUsers = filteredUsers.slice(start, end);

  return (
    <div className="bg-white p-3 h-[87vh] overflow-auto">
      <div className="flex justify-between">
        <Navigate title={"User Management"} />

        <div className="flex gap-4">
          <Select
            value={statusFilter}
            onChange={(val) => {
              setStatusFilter(val);
              setCurrentPage(1);
            }}
            options={[
              { value: "All", label: "All Active" },
              { value: "Blocked", label: "Blocked Users" },
              { value: "Hidden", label: "Hidden Users" },
              { value: "Deleted", label: "Deleted Users" },
            ]}
            style={{ maxWidth: "300px", minWidth: "150px", height: "40px" }}
          />

          <Input
            placeholder="Search by name or email..."
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ maxWidth: "300px", height: "40px" }}
          />
        </div>
      </div>

      <Table
        dataSource={paginatedUsers}
        columns={columns}
        pagination={false}
        scroll={{ x: "max-content" }}
        rowKey="id"
      />

      <div className="mt-4 flex justify-center">
        <Pagination
          current={currentPage}
          pageSize={pageSize}
          total={filteredUsers.length}
          onChange={handlePageChange}
        />
      </div>

      {/* ✅ Modal */}
      <Modal
        open={isModalOpen2}
        centered
        onCancel={handleCancel2}
        footer={null}
      >
        {selectedUser && (
          <div className="p-5">
            <div className="flex flex-col items-center">
              <img
                src={selectedUser.profile_photo_url || `https://ui-avatars.com/api/?name=${selectedUser.name || selectedUser.email}`}
                className="w-24 h-24 rounded-full object-cover border-4 border-blue-200 mb-3"
                alt=""
              />
              <h2 className="text-xl font-bold">{selectedUser.name || "Unknown"}</h2>
              <p className="text-gray-500 text-sm">{selectedUser.email}</p>
            </div>

            <div className="mt-6 space-y-3">
              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span>Location</span>
                <span>{selectedUser.location_city || "Unknown"}</span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span>Partner Connection</span>
                <span>{selectedUser.partner ? "Connected" : "None"}</span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span>Aligned Status</span>
                <span className="text-blue-600">
                  {selectedUser.is_aligned ? "Aligned" : "Not Aligned"}
                </span>
              </div>

              <div className="flex justify-between bg-gray-50 p-3 rounded-lg">
                <span>Status</span>
                <span className={selectedUser.is_deleted ? "text-red-600" : selectedUser.is_blocked ? "text-red-600" : "text-green-600"}>
                  {selectedUser.is_deleted ? "Deleted" : selectedUser.is_blocked ? "Blocked" : selectedUser.is_hidden ? "Hidden" : "Active"}
                </span>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default UserManagement;
