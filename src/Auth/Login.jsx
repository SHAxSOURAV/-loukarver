
import React, { useState } from "react";
import { Form, Input, Button, Checkbox, message } from "antd";
import { FaEye, FaEyeSlash, FaGoogle, FaFacebookF } from "react-icons/fa";
import { Link, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { setToken } from "../page/redux/features/auth/authSlice";

const Login = () => {

    const [form] = Form.useForm();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      console.log("Form Values:", values);
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/admin-signin`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: values.email,
          password: values.password,
        }),
      });
      const payload = await response.json();
      
      if (response.ok && payload.access_token) {
        dispatch(setToken({ token: payload.access_token, rememberMe: values.remember }));
        message.success("Login successful!");
        navigate("/");
      } else {
        message.error(payload.detail || "Login failed!");
      }
    } catch (error) {
      console.error("Login error:", error);
      message.error("Something went wrong. Try again!");
    } finally {
      setLoading(false);
    }
  };
  return (
 <div className="flex justify-center items-center min-h-screen px-4 lg:px-0">
      <div className="w-full max-w-lg  lg:p-8 p-4 border">
        {/* Title */}
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Sign In</h2>
        <p className="text-gray-600 mb-6 text-sm">
          Enter your email address or choose a different way to sign in to
          Custom Ink.
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
            <Input
              style={{ height: "50px" }}
              placeholder="Enter Email Address"
            />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[{ required: true, message: "Please input your password!" }]}
          >
            <Input.Password
              style={{ height: "50px" }}
              className=""
              placeholder="••••••••"
            />
          </Form.Item>

          <div className="flex flex-col gap-2 mb-6 text-sm">
            <div className="flex items-center justify-between">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox className="text-gray-700">Remember me</Checkbox>
              </Form.Item>
              <Link
                to={"/forgot-password"}
                className="text-sm text-[#2F799E] hover:underline focus:outline-none"
              >
                Forget password?
              </Link>
            </div>
            
            <div className="text-center mt-2">
              <span className="text-gray-600">
                Don't have an account?{" "}
                <Link to="/signup" className="text-[#8B4513] hover:underline font-medium">
                  Sign up
                </Link>
              </span>
            </div>
          </div>

          {/* Continue Button */}
          <Form.Item>
            <button
              htmlType="submit"
              className="w-full bg-[#8B4513] py-3 text-white rounded-md hover:bg-primary-dark transition-colors"
            >
              Continue
            </button>
          </Form.Item>
        </Form>


       
      </div>
    </div>
  );
};

export default Login;
