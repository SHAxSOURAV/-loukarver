import React, { useState, useEffect } from "react";
import { message, Modal } from "antd";
import { FaRegQuestionCircle } from "react-icons/fa";
import { RiDeleteBin6Line } from "react-icons/ri";
import { CiEdit } from "react-icons/ci";
import { useSelector } from "react-redux";
import { Navigate } from "../../Navigate";

const FAQ = () => {
  const [isAccordionOpen, setIsAccordionOpen] = useState(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedFaq, setSelectedFaq] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const { token } = useSelector((state) => state.logInUser);
  const [faqs, setFaqs] = useState([]);

  useEffect(() => {
    fetchFaqs();
  }, []);

  const fetchFaqs = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/faq`);
      if (res.ok) {
        const data = await res.json();
        setFaqs(data);
      }
    } catch (error) {
      console.error("Failed to fetch FAQs:", error);
    }
  };

  // Accordion click
  const handleClick = (index) => {
    setIsAccordionOpen((prevIndex) => (prevIndex === index ? null : index));
  };

  // Add FAQ
  const handleAddFaq = async () => {
    if (!question || !answer) return message.warning("Please fill all fields");
    
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/faq`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ question, answer })
      });
      
      if (res.ok) {
        message.success("FAQ added successfully");
        fetchFaqs();
        setAddModalOpen(false);
        setQuestion("");
        setAnswer("");
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to add FAQ");
      }
    } catch (error) {
      message.error("An error occurred");
    }
  };

  // Update FAQ
  const handleUpdateFaq = async () => {
    if (!question || !answer) return message.warning("Please fill all fields");
    
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/faq/${selectedFaq.id || selectedFaq._id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ question, answer })
      });
      
      if (res.ok) {
        message.success("FAQ updated successfully");
        fetchFaqs();
        setUpdateModalOpen(false);
        setSelectedFaq(null);
        setQuestion("");
        setAnswer("");
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to update FAQ");
      }
    } catch (error) {
      message.error("An error occurred");
    }
  };

  // Delete FAQ
  const handleDeleteFaq = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/faq/${selectedFaq.id || selectedFaq._id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        message.success("FAQ deleted successfully");
        fetchFaqs();
        setDeleteModalOpen(false);
        setSelectedFaq(null);
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to delete FAQ");
      }
    } catch (error) {
      message.error("An error occurred");
    }
  };

  return (
    <div className="relative bg-white p-3 h-[87vh]">
      <div className="flex justify-between items-center">
         <Navigate title={"Faq"} />
        <button
          onClick={() => setAddModalOpen(true)}
          className="bg-[#E63946] text-white font-semibold px-5 py-2 rounded transition duration-200"
        >
          + Add FAQ
        </button>
      </div>

      <div className="flex gap-2 flex-col w-full mt-5 p-5">
        {faqs.map((faq, index) => (
          <section key={faq._id} className="border-b border-[#e5eaf2] rounded py-3">
            <div
              className="flex gap-2 cursor-pointer items-center justify-between w-full"
              onClick={() => handleClick(index)}
            >
              <h2 className="text-base font-normal md:font-bold md:text-2xl flex gap-2 items-center">
                <FaRegQuestionCircle className="w-5 h-5 hidden md:flex" />
                {faq.question}
              </h2>
              <div className="flex gap-2 md:gap-4 items-center">
                <div className="border-2 px-1.5 py-1 rounded border-[#E63946] bg-[#f0fcf4]">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFaq(faq);
                      setQuestion(faq.question);
                      setAnswer(faq.answer);
                      setUpdateModalOpen(true);
                    }}
                  >
                    <CiEdit className="text-2xl cursor-pointer text-[#E63946] font-bold transition-all" />
                  </button>
                </div>
                <div className="border-2 px-1.5 py-1 rounded border-[#E63946] bg-[#f0fcf4]">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFaq(faq);
                      setDeleteModalOpen(true);
                    }}
                  >
                    <RiDeleteBin6Line className="text-2xl cursor-pointer text-red-500 transition-all" />
                  </button>
                </div>
              </div>
            </div>
            <div
              className={`grid transition-all duration-300 overflow-hidden ease-in-out ${
                isAccordionOpen === index ? "grid-rows-[1fr] opacity-100 mt-4" : "grid-rows-[0fr] opacity-0"
              }`}
            >
              <p className="text-[#424242] text-[0.9rem] overflow-hidden">{faq.answer}</p>
            </div>
          </section>
        ))}
      </div>

      {/* Add FAQ Modal */}
      <Modal open={addModalOpen} centered onCancel={() => setAddModalOpen(false)} footer={null}>
        <div className="p-5">
          <h2 className="text-2xl font-bold text-center mb-2">Add FAQ</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Question</label>
              <input
                type="text"
                placeholder="Enter the FAQ"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Answer</label>
              <textarea
                placeholder="Enter the FAQ Answer"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-6">
            <button
              onClick={() => setAddModalOpen(false)}
              className="py-2 px-4 rounded-lg border border-[#EF4444] bg-red-50"
            >
              Cancel
            </button>
            <button onClick={handleAddFaq} className="py-2 px-4 rounded-lg bg-[#E63946] text-white">
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* Update FAQ Modal */}
      <Modal open={updateModalOpen} centered onCancel={() => setUpdateModalOpen(false)} footer={null}>
        <div className="p-5">
          <h2 className="text-2xl font-bold text-center mb-2">Update FAQ</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Question</label>
              <input
                type="text"
                placeholder="Enter the FAQ"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Answer</label>
              <textarea
                placeholder="Enter the FAQ Answer"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-6">
            <button
              onClick={() => setUpdateModalOpen(false)}
              className="py-2 px-4 rounded-lg border border-[#EF4444] bg-red-50"
            >
              Cancel
            </button>
            <button onClick={handleUpdateFaq} className="py-2 px-4 rounded-lg bg-[#E63946] text-white">
              Save
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete FAQ Modal */}
      <Modal open={deleteModalOpen} centered onCancel={() => setDeleteModalOpen(false)} footer={null}>
        <div className="p-5 text-center">
          <h2 className="text-2xl font-bold mb-6">Are you sure you want to delete?</h2>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setDeleteModalOpen(false)}
              className="py-2 px-4 rounded-lg border border-[#EF4444] bg-red-50"
            >
              Cancel
            </button>
            <button onClick={handleDeleteFaq} className="py-2 px-4 rounded-lg bg-[#E63946] text-white">
              Delete
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default FAQ;