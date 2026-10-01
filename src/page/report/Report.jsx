import React, { useState, useEffect } from "react";
import {
  Input,
  Pagination,
  Select,
  Table,
  DatePicker,
  Modal,
  Button,
  Tag,
  message
} from "antd";
import { SearchOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { Navigate } from "../../Navigate";
import { useSelector } from "react-redux";

const Report = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selectedDate, setSelectedDate] = useState(null);
  
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);

  // Chat Modal State
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [sending, setSending] = useState(false);

  const pageSize = 10;
  const { token } = useSelector((state) => state.logInUser);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/reports?status=${statusFilter}&search=${searchText}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setReports(data);
      }
    } catch (e) {
      message.error("Failed to fetch reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchReports();
  }, [token, statusFilter, searchText]);

  const fetchMessages = async (reportId) => {
    setChatLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/reports/${reportId}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      message.error("Failed to load chat");
    } finally {
      setChatLoading(false);
    }
  };

  const handleOpenChat = (record) => {
    setSelectedReport(record);
    setIsModalVisible(true);
    fetchMessages(record.id);
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;
    setSending(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/reports/${selectedReport.id}/messages`, {
        method: "POST",
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: newMessage.trim() })
      });
      if (res.ok) {
        setNewMessage("");
        fetchMessages(selectedReport.id);
      }
    } catch (e) {
      message.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handleChangeStatus = async (newStatus) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/admin/reports/${selectedReport.id}/status`, {
        method: "PATCH",
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status: newStatus })
      });
      if (res.ok) {
        message.success(`Status updated to ${newStatus}`);
        setSelectedReport({ ...selectedReport, status: newStatus });
        fetchReports();
      }
    } catch (e) {
      message.error("Failed to change status");
    }
  };

  // ✅ Filtering (Client-side date filtering since it's easy)
  const filteredData = reports.filter((item) => {
    const matchDate = selectedDate
      ? dayjs(item.created_at).isSame(selectedDate, "day")
      : true;
    return matchDate;
  });

  // Pagination
  const start = (currentPage - 1) * pageSize;
  const paginatedData = filteredData.slice(start, start + pageSize);

  // ✅ Columns
  const columns = [
    {
      title: "User",
      render: (_, record) => (
        <div className="flex items-center gap-3">
          <img
            src={record.user_image || `https://ui-avatars.com/api/?name=${record.user_name}`}
            className="w-10 h-10 rounded-full object-cover bg-gray-200"
            alt=""
          />
          <div>
            <p className="font-medium">{record.user_name}</p>
            <p className="text-xs text-gray-500">
              {record.user_email}
            </p>
          </div>
        </div>
      ),
    },
    {
      title: "Title",
      dataIndex: "title",
    },
    {
      title: "Date",
      dataIndex: "created_at",
      render: (text) => dayjs(text).format("YYYY-MM-DD"),
    },
    {
      title: "Status",
      dataIndex: "status",
      render: (text) => {
        let color = "gray";
        if (text === "Resolved") color = "green";
        if (text === "Pending") color = "orange";
        if (text === "In Progress") color = "blue";
        if (text === "Rejected") color = "red";
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: "Action",
      render: (_, record) => (
        <Button onClick={() => handleOpenChat(record)}>View Ticket</Button>
      )
    }
  ];

  return (
    <div className="bg-white p-3 h-[87vh] overflow-auto">
      <div className="flex justify-between mb-4">
        <Navigate title={"Report"} />

        <div className="flex gap-3 ">
          {/* Search */}
          <Input
            placeholder="Search..."
            prefix={<SearchOutlined />}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ maxWidth: "200px", height: "40px" }}
          />

          {/* ✅ Single DatePicker */}
          <DatePicker
            onChange={(date) => setSelectedDate(date)}
            style={{ maxWidth: "300px", height: "40px" }}
          />

          {/* Status Filter */}
          <Select
            placeholder="Sort by Status"
            value={statusFilter}
            onChange={(val) => setStatusFilter(val || "All")}
            allowClear
            options={[
              { value: "All", label: "All" },
              { value: "Pending", label: "Pending" },
              { value: "In Progress", label: "In Progress" },
              { value: "Resolved", label: "Resolved" },
              { value: "Rejected", label: "Rejected" },
            ]}
            style={{ maxWidth: "200px", height: "40px" }}
          />
        </div>
      </div>

      <Table
        dataSource={paginatedData}
        columns={columns}
        pagination={false}
        rowKey="id"
        loading={loading}
      />

      <div className="mt-4 flex justify-center">
        <Pagination
          current={currentPage}
          pageSize={pageSize}
          total={filteredData.length}
          onChange={(page) => setCurrentPage(page)}
        />
      </div>

      {/* Chat Modal */}
      <Modal
        title={`Ticket: ${selectedReport?.title}`}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={800}
        destroyOnClose
      >
        {selectedReport && (
          <div className="flex flex-col h-[60vh]">
            <div className="flex justify-between items-center mb-4 pb-2 border-b">
              <div>
                <p className="font-semibold">{selectedReport.user_name}</p>
                <p className="text-sm text-gray-500">{selectedReport.user_email}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Change Status:</span>
                <Select
                  value={selectedReport.status}
                  onChange={handleChangeStatus}
                  style={{ width: 120 }}
                  options={[
                    { value: "Pending", label: "Pending" },
                    { value: "In Progress", label: "In Progress" },
                    { value: "Resolved", label: "Resolved" },
                    { value: "Rejected", label: "Rejected" },
                  ]}
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto pr-2 flex flex-col gap-3">
              {chatLoading ? (
                <div className="text-center text-gray-500 mt-10">Loading messages...</div>
              ) : messages.length === 0 ? (
                <div className="text-center text-gray-500 mt-10">No messages yet.</div>
              ) : (
                messages.map((msg) => {
                  const isAdmin = msg.sender_type === "admin";
                  return (
                    <div key={msg.id} className={`flex flex-col ${isAdmin ? "items-end" : "items-start"}`}>
                      <div className={`px-4 py-2 rounded-xl max-w-[70%] ${isAdmin ? "bg-blue-600 text-white rounded-br-none" : "bg-gray-100 text-gray-800 rounded-bl-none"}`}>
                        <p>{msg.message}</p>
                        {msg.file_url && (
                          <img src={msg.file_url} alt="attachment" className="mt-2 rounded-lg max-w-full h-auto max-h-[200px]" />
                        )}
                      </div>
                      <span className="text-xs text-gray-400 mt-1">
                        {dayjs(msg.created_at).format("MMM D, HH:mm")}
                      </span>
                    </div>
                  );
                })
              )}
            </div>

            <div className="mt-4 pt-4 border-t flex gap-2">
              <Input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onPressEnter={handleSendMessage}
                placeholder="Type your reply..."
                disabled={sending}
              />
              <Button type="primary" onClick={handleSendMessage} loading={sending}>
                Send
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Report;