
import React, { useState } from "react";
import { Form, Input, Button, message } from "antd";
import { FaEye, FaEyeSlash } from "react-icons/fa";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { setToken } from "../page/redux/features/auth/authSlice";

const ResetPass = () => {
  const [form] = Form.useForm();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  const { email, otp } = location.state || {};

  const onFinish = async (values) => {
    if (!email || !otp) {
      return message.error("Missing email or OTP. Please try resetting again.");
    }
    
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          otp,
          new_password: values.password
        }),
      });
      const data = await response.json();
      
      if (response.ok && data.access_token) {
        dispatch(setToken({ token: data.access_token, rememberMe: true }));
        message.success("Password reset successfully! You are now logged in.");
        navigate("/");
      } else {
        message.error(data.detail || "Failed to reset password.");
      }
    } catch (e) {
      message.error("Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen px-4 lg:px-0">
      <div className="w-full max-w-lg lg:p-8 p-4 border rounded-lg">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Set a New Password
        </h2>
        <p className="text-gray-600 mb-6 text-sm">
          Secure your account by creating a new password.
        </p>

        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item
            label="Enter New Password"
            name="password"
            rules={[
              { required: true, message: "Please enter your password!" },
              { min: 6, message: "Password must be at least 6 characters!" },
            ]}
          >
            <Input
              style={{height:'50px'}}
              type={showPassword ? "text" : "password"}
              placeholder="Enter New Password"
              suffix={
                <span
                  className="cursor-pointer text-gray-500"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <FaEyeSlash /> : <FaEye />}
                </span>
              }
            />
          </Form.Item>

          <Form.Item
            label="Confirm New Password"
            name="confirmPassword"
            dependencies={["password"]}
            rules={[
              { required: true, message: "Please confirm your password!" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error("Passwords do not match!"));
                },
              }),
            ]}
          >
            <Input
              style={{height:'50px'}}
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Confirm New Password"
              suffix={
                <span
                  className="cursor-pointer text-gray-500"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? <FaEyeSlash /> : <FaEye />}
                </span>
              }
            />
          </Form.Item>

          <Form.Item>
            <button
              type="submit"
              disabled={loading}
              className={`w-full bg-[#8B4513] py-3 text-white rounded-md transition-colors ${loading ? "opacity-70" : "hover:bg-[#6A320A]"}`}
            >
              {loading ? "Resetting..." : "Continue"}
            </button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
};

export default ResetPass;
