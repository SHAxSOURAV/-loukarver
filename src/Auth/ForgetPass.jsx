import React, { useState } from "react";
import { Form, Input, Button, message } from "antd";
import { FaEye, FaEyeSlash, FaGoogle, FaFacebookF } from "react-icons/fa";
import { Link, useNavigate } from "react-router-dom";


const ForgetPass = () => {
  
  const [form] = Form.useForm();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: values.email }),
      });
      const data = await response.json();
      if (response.ok) {
        message.success(data.message || "OTP sent!");
        navigate("/verification", { state: { email: values.email, type: "forgot" } });
      } else {
        message.error(data.detail || "Failed to send OTP");
      }
    } catch (e) {
      message.error("Something went wrong");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="flex justify-center items-center min-h-screen px-4 lg:px-0">
      <div className="w-full max-w-lg  lg:p-8 p-4 border">
        {/* Title */}
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Forgot Password</h2>
        <p className="text-gray-600 mb-6 text-sm">
          Enter your email address to receive an OTP to reset your password.
        </p>

        {/* Ant Design Form */}
        <Form form={form} layout="vertical" onFinish={onFinish}>
          {/* Email */}
          <Form.Item
            label="Enter Email Address"
            name="email"
            rules={[
              { required: true, message: "Please enter your email!" },
              { type: "email", message: "Enter a valid email!" },
            ]}
          >
            <Input style={{height:'50px'}} placeholder="Enter Email Address" />
          </Form.Item>

          {/* Continue Button */}
          <Form.Item>
            <button
              htmlType="submit"
              disabled={loading}
              className={`w-full bg-[#8B4513] py-3 text-white rounded-md transition-colors ${loading ? "opacity-70" : "hover:bg-[#6A320A]"}`}
            >
              {loading ? "Sending..." : "Continue"}
            </button>
          </Form.Item>
        </Form>

        {/* Terms */}
      
      </div>
    </div>
  );
};

export default ForgetPass;
