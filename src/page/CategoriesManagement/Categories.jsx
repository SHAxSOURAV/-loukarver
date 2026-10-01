import { Input, message, Pagination, Table } from "antd";
import { useState } from "react";
import { MdOutlineModeEdit } from "react-icons/md";
import { RiDeleteBin6Line } from "react-icons/ri";
import { useNavigate } from "react-router-dom";
import AddCategories from "./AddCategories";
import EditCategories from "./EditCategories";
import { Navigate } from "../../Navigate";
import { SearchOutlined } from "@ant-design/icons";

const Categories = () => {
  const [deleteCategory] = useState(); // Placeholder, not used
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;
  const [categories, setCategories] = useState([
    {
      _id: "1",
      name: "Electronics",
      imageUrl: "https://via.placeholder.com/100x100/007BFF/ffffff?text=Electronics"
    },
    {
      _id: "2",
      name: "Clothing",
      imageUrl: "https://via.placeholder.com/100x100/E63946/ffffff?text=Clothing"
    },
    {
      _id: "3",
      name: "Books",
      imageUrl: "https://via.placeholder.com/100x100/28A745/ffffff?text=Books"
    },
    {
      _id: "4",
      name: "Home & Garden",
      imageUrl: "https://via.placeholder.com/100x100/FFC107/000000?text=Home"
    },
    {
      _id: "5",
      name: "Sports",
      imageUrl: "https://via.placeholder.com/100x100/DC3545/ffffff?text=Sports"
    },
    {
      _id: "6",
      name: "Automotive",
      imageUrl: "https://via.placeholder.com/100x100/6F42C1/ffffff?text=Auto"
    },
    {
      _id: "7",
      name: "Toys",
      imageUrl: "https://via.placeholder.com/100x100/20C997/ffffff?text=Toys"
    },
    {
      _id: "8",
      name: "Health",
      imageUrl: "https://via.placeholder.com/100x100/FD7E14/ffffff?text=Health"
    },
    {
      _id: "9",
      name: "Beauty",
      imageUrl: "https://via.placeholder.com/100x100/198754/ffffff?text=Beauty"
    },
    {
      _id: "10",
      name: "Food & Grocery",
      imageUrl: "https://via.placeholder.com/100x100/0DCAF0/000000?text=Food"
    },
    {
      _id: "11",
      name: "Jewelry",
      imageUrl: "https://via.placeholder.com/100x100/6610F2/ffffff?text=Jewelry"
    },
    {
      _id: "12",
      name: "Shoes",
      imageUrl: "https://via.placeholder.com/100x100/17A2B8/ffffff?text=Shoes"
    },
    {
      _id: "13",
      name: "Furniture",
      imageUrl: "https://via.placeholder.com/100x100/343A40/ffffff?text=Furniture"
    },
    {
      _id: "14",
      name: "Music",
      imageUrl: "https://via.placeholder.com/100x100/E83E8C/ffffff?text=Music"
    },
    {
      _id: "15",
      name: "Movies",
      imageUrl: "https://via.placeholder.com/100x100/6C757D/ffffff?text=Movies"
    }
  ]);
  const [openAddModal, setOpenAddModal] = useState(false);
  const [editModal, setEditModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const isLoading = false; // Static for dummy data
  const imageUrl = ""; // Dummy base URL, images are full URLs

  // Filter categories based on search
  const filteredCategories = categories.filter((cat) =>
    cat.name.toLowerCase().includes(search.toLowerCase())
  );

  // Paginate filtered data
  const total = filteredCategories.length;
  const paginatedData = filteredCategories.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const handlePageChange = (page) => setCurrentPage(page);

  const handleDeleteCategory = (id) => {
    setCategories((prev) => prev.filter((cat) => cat._id !== id));
    message.success("Category deleted successfully");
    // Adjust page if current page is now empty
    if (paginatedData.length === 1 && currentPage > 1) {
      setCurrentPage((prev) => Math.max(1, prev - 1));
    }
  };

  // ✏️ Edit Handler
  const handleEdit = (record) => {
    setSelectedCategory(record);
    setEditModal(true);
  };

  // 📝 Table Columns
  const columns = [
    {
      title: "SL No.",
      dataIndex: "sl",
      key: "sl",
      render: (_, __, index) => (currentPage - 1) * pageSize + (index + 1),
    },
    {
      title: "Image",
      dataIndex: "image",
      key: "image",
      align: "center",
      render: (_, record) => (
        <img
          src={record.imageUrl}
          alt={record.name}
          className="w-10 h-10 object-cover rounded mx-auto"
        />
      ),
    },
    {
      title: "Category Name",
      dataIndex: "name",
      key: "name",
      align: "center",
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      render: (_, record) => (
        <div className="flex gap-2 justify-end">
          <div
            onClick={() => handleEdit(record)}
            className="w-[36px] h-[36px] text-lg bg-[#007BFF] flex justify-center items-center text-white rounded cursor-pointer"
          >
            <MdOutlineModeEdit />
          </div>
          <div
            onClick={() => handleDeleteCategory(record._id)}
            className="w-[36px] h-[36px] text-lg bg-[#E63946] flex justify-center items-center text-white rounded cursor-pointer"
          >
            <RiDeleteBin6Line />
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="bg-white p-3 h-[87vh]">
      <div className="flex justify-between mb-4">
        <Navigate title={"Category"} />
        <div className="flex gap-5">
          <Input
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1); // Reset to first page on search
            }}
            placeholder="Search by name..."
            prefix={<SearchOutlined />}
            style={{ maxWidth: "500px", height: "40px" }}
          />
          <div>
            {" "}
            <button
              onClick={() => setOpenAddModal(true)}
              className="bg-[#E63946] w-[150px] text-white py-2 rounded"
            >
              Add Category
            </button>
          </div>
        </div>
      </div>

      <Table
        dataSource={paginatedData}
        columns={columns}
        rowKey="_id"
        pagination={false}
        className="custom-table"
        scroll={{ x: "max-content" }}
        loading={isLoading}
      />

      <div className="mt-4 flex justify-center">
        <Pagination
          current={currentPage}
          pageSize={pageSize}
          total={total}
          onChange={handlePageChange}
          showSizeChanger={false}
        />
      </div>

      <AddCategories
        openAddModal={openAddModal}
        setOpenAddModal={setOpenAddModal}
      />
      <EditCategories
        editModal={editModal}
        setEditModal={setEditModal}
        selectedCategory={selectedCategory}
      />
    </div>
  );
};

export default Categories;