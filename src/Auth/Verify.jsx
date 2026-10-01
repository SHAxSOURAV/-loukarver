import React, { useState } from "react";
import { message } from "antd";
import { Link, useLocation, useNavigate } from "react-router-dom";
import OTPInput from "react-otp-input";
import { useDispatch } from "react-redux";
import { setToken } from "../page/redux/features/auth/authSlice";

const Verify = () => {
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  const { email, type } = location.state || {};

  const handleVerify = async () => {
    if (!email) {
      return message.error("Email is missing. Please try again.");
    }
    if (otp.length !== 6) {
      return message.error("Please enter a valid 6-digit OTP.");
    }

    if (type === "forgot") {
      // Just pass the OTP to the reset-password page
      navigate("/reset-password", { state: { email, otp } });
    } else {
      // Signup flow: Verify the OTP and get token
      setLoading(true);
      try {
        const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/verify-email`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, otp }),
        });
        const data = await response.json();
        
        if (response.ok && data.access_token) {
          dispatch(setToken({ token: data.access_token, rememberMe: true }));
          message.success("Email verified successfully! You are now logged in.");
          navigate("/");
        } else {
          message.error(data.detail || "Verification failed");
        }
      } catch (e) {
        message.error("Something went wrong");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleResend = async () => {
    if (!email) return;
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/resend-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (response.ok) {
        message.success(data.message || "OTP resent successfully");
      } else {
        message.error(data.detail || "Failed to resend OTP");
      }
    } catch (e) {
      message.error("Something went wrong resending OTP");
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen px-4 lg:px-0">
      <div className="w-full max-w-lg  p-8 border rounded-lg">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">
          Check your email
        </h2>
        <p className="text-gray-600 mb-6 text-sm">
          We sent a 6-digit code to <span className="font-semibold">{email || "your email"}</span>. Enter the code to continue.
        </p>

        <div className="flex justify-center mb-5">
          <OTPInput
            value={otp}
            onChange={setOtp}
            numInputs={6}
            renderSeparator={<span className="mx-1"></span>}
            renderInput={(props) => (
              <input
                {...props}
                className="w-16 h-16 text-center bg-white text-lg border rounded-md focus:outline-none focus:ring-2 focus:ring-[#8B4513]"
                style={{ width: "40px", height: "50px" }}
              />
            )}
          />
        </div>
        
        <button
          onClick={handleVerify}
          disabled={loading}
          className={`w-full bg-[#8B4513] py-3 text-white rounded-md transition-colors ${loading ? "opacity-70" : "hover:bg-[#6A320A]"}`}
        >
          {loading ? "Verifying..." : "Continue"}
        </button>

        <div className="flex justify-center mt-4">
          <span className="text-gray-600">
            Have not received the email?{" "}
            <span
              onClick={handleResend}
              className="text-[#8B4513] hover:underline cursor-pointer font-medium pl-1"
            >
              Resend
            </span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default Verify;
