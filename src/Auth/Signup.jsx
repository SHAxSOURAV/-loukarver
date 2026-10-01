import React, { useState } from "react";
import { Form, Input, Button, Checkbox, message } from "antd";
import { Link, useNavigate } from "react-router-dom";

const Signup = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      console.log("Form Values:", values);
      
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/admin-signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: values.name,
          email: values.email,
          password: values.password,
          admin_secret: values.admin_secret
        }),
      });
      
      const payload = await response.json();
      console.log("API Response:", payload);
      
      if (response.ok && payload?.success) {
        message.success(payload.message || "Signup successful! Check email for OTP.");
        navigate("/verification", { state: { email: values.email, type: "signup" } });
      } else {
        message.error(payload?.detail || payload?.message || "Signup failed!");
      }
    } catch (error) {
      console.error("Signup error:", error);
      message.error("Something went wrong. Try again!");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen px-4 lg:px-0 bg-[#f9fafb]">
      <div className="w-full max-w-lg lg:p-8 p-6 bg-white border rounded-xl shadow-sm">
        {/* Title */}
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Create an Account</h2>
        <p className="text-gray-600 mb-6 text-sm">
          Sign up to access the Samesy admin dashboard.
        </p>

        {/* Ant Design Form */}
        <Form form={form} layout="vertical" onFinish={onFinish}>
          {/* Name */}
          <Form.Item
            label="Full Name"
            name="name"
            rules={[
              { required: true, message: "Please enter your full name!" },
            ]}
          >
            <Input
              style={{ height: "50px" }}
              placeholder="Enter your full name"
            />
          </Form.Item>

          {/* Email */}
          <Form.Item
            label="Email Address"
            name="email"
            rules={[
              { required: true, message: "Please enter your email!" },
              { type: "email", message: "Enter a valid email!" },
            ]}
          >
            <Input
              style={{ height: "50px" }}
              placeholder="Enter your email address"
            />
          </Form.Item>

          {/* Password */}
          <Form.Item
            label="Password"
            name="password"
            rules={[
              { required: true, message: "Please input your password!" },
              { min: 6, message: "Password must be at least 6 characters!" }
            ]}
          >
            <Input.Password
              style={{ height: "50px" }}
              placeholder="••••••••"
            />
          </Form.Item>

          {/* Admin Secret */}
          <Form.Item
            label="Admin Creation Secret"
            name="admin_secret"
            tooltip="Provide the secret key to register as an Administrator."
            rules={[
              { required: true, message: "Admin secret is required!" }
            ]}
          >
            <Input.Password
              style={{ height: "50px" }}
              placeholder="Enter Admin Secret"
            />
          </Form.Item>

          <div className="flex items-center justify-between mb-6 mt-2 text-sm">
            <span className="text-gray-600">
              Already have an account?{" "}
              <Link to="/login" className="text-[#8B4513] hover:underline font-medium">
                Log in
              </Link>
            </span>
          </div>

          {/* Continue Button */}
          <Form.Item>
            <button
              type="submit"
              disabled={loading}
              className={`w-full bg-[#8B4513] py-3 text-white rounded-md transition-colors ${loading ? "opacity-70" : "hover:bg-[#6A320A]"}`}
            >
              {loading ? "Signing up..." : "Create Account"}
            </button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
};

export default Signup;
