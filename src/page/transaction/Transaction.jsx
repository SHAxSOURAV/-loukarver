import { DatePicker, Input, Modal, Select, Table } from "antd";
import React, { useState } from "react";

import { Navigate } from "../../Navigate";
import { SearchOutlined } from "@ant-design/icons";



import { MdOutlineAttachMoney } from "react-icons/md";
import { AiOutlineCheckCircle } from "react-icons/ai";
import { MdPendingActions } from "react-icons/md";
import { AiOutlineCloseCircle } from "react-icons/ai";


const Transaction = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // ✅ Demo Data (replace with API later)
  const paginatedUsers = [
  {
    key: 1,
    transactionId: "TXN001",
    name: "John Doe",
    email: "john@example.com",
    image: "https://i.pravatar.cc/150?img=1",
    date: "2024-03-01",
    type: "Credit",
    amount: "$120",
    status: "Completed",
  },
  {
    key: 2,
    transactionId: "TXN002",
    name: "Sarah Smith",
    email: "sarah@example.com",
    image: "https://i.pravatar.cc/150?img=2",
    date: "2024-03-02",
    type: "Debit",
    amount: "$80",
    status: "Pending",
  },
];
  // ✅ Modal handlers
  const showModal = (record) => {
    setSelectedUser(record);
    setIsModalOpen(true);
  };

  const handleCancel = () => {
    setIsModalOpen(false);
    setSelectedUser(null);
  };

  const handleBlock = (user) => {
    console.log("Block user:", user);
  };

  const handleDelete = (user) => {
    console.log("Delete user:", user);
  };

  // ✅ Table Columns
  const columns = [
  {
    title: "Transaction ID",
    dataIndex: "transactionId",
  },
  {
    title: "User",
    render: (_, record) => (
      <div className="flex items-center gap-3">
        <img
          src={record.image}
          className="w-10 h-10 object-cover rounded-full border"
          alt=""
        />
        <div>
          <p className="font-medium">{record.name}</p>
          <p className="text-xs text-gray-500">{record.email}</p>
        </div>
      </div>
    ),
  },
  {
    title: "Date",
    dataIndex: "date",
  },
  {
    title: "Type",
    dataIndex: "type",
    render: (text) => (
      <span
        className={`px-2 py-1 rounded text-xs ${
          text === "Credit"
            ? "bg-green-100 text-green-600"
            : "bg-red-100 text-red-600"
        }`}
      >
        {text}
      </span>
    ),
  },
  {
    title: "Amount",
    dataIndex: "amount",
  },
  {
    title: "Status",
    dataIndex: "status",
    render: (text) => {
      const statusStyle = {
        Completed: "bg-green-100 text-green-600",
        Pending: "bg-orange-100 text-orange-600",
        Failed: "bg-red-100 text-red-600",
      };

      return (
        <span
          className={`px-2 py-1 rounded text-xs ${statusStyle[text]}`}
        >
          {text}
        </span>
      );
    },
  },
];
  return (
    <div className="bg-white p-3 h-[87vh] overflow-auto">
      <Navigate title={"Transaction History"} />
      <div className="grid grid-cols-4 gap-4">
  {/* Total Revenue */}
  <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
    <div className="bg-green-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
      <MdOutlineAttachMoney className="text-green-600" />
    </div>
    <div>
      <h1 className="font-semibold text-2xl">$50k</h1>
      <h1 className="text-zinc-500">Total Revenue</h1>
    </div>
  </div>

  {/* Completed */}
  <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
    <div className="bg-blue-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
      <AiOutlineCheckCircle className="text-blue-600" />
    </div>
    <div>
      <h1 className="font-semibold text-2xl">100</h1>
      <h1 className="text-zinc-500">Completed</h1>
    </div>
  </div>

  {/* Pending */}
  <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
    <div className="bg-yellow-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
      <MdPendingActions className="text-yellow-600" />
    </div>
    <div>
      <h1 className="font-semibold text-2xl">65</h1>
      <h1 className="text-zinc-500">Pending</h1>
    </div>
  </div>

  {/* Failed */}
  <div className="flex gap-4 items-center bg-white p-6 rounded shadow">
    <div className="bg-red-100 w-[55px] rounded-full h-[55px] flex justify-center items-center text-3xl">
      <AiOutlineCloseCircle className="text-red-600" />
    </div>
    <div>
      <h1 className="font-semibold text-2xl">5</h1>
      <h1 className="text-zinc-500">Failed</h1>
    </div>
  </div>
</div>
      <div className="flex gap-4 justify-end mt-4 mb-2">
        <Select
          placeholder="Sort by Status"
          options={[
            { value: "Active", label: "Active" },
            { value: "Blocked", label: "Blocked" },
          ]}
          style={{ maxWidth: "300px", height: "40px" }}
        />

       <DatePicker
          
            style={{ maxWidth: "300px", height: "40px" }}
          />
        <Input
          placeholder="Search by name..."
          prefix={<SearchOutlined />}
          style={{ maxWidth: "300px", height: "40px" }}
        />
        <div>
          <button className="bg-[#C09B7A80] py-2 text-[#8B4513] px-5 rounded">
            Export
          </button>
        </div>
      </div>
      <Table
        dataSource={paginatedUsers}
        columns={columns}
        pagination={false}
        scroll={{ x: "max-content" }}
      />

      {/* ✅ Modal */}
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
              <h2 className="text-xl font-bold">{selectedUser.name}</h2>
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
                onClick={() => handleBlock(selectedUser)}
                className="flex-1 bg-red-500 text-white py-2 rounded-lg"
              >
                Block
              </button>
              <button
                onClick={() => handleDelete(selectedUser)}
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

export default Transaction;
