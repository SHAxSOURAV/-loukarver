import { Button, Form, Input, message } from "antd";
import React, { useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";

export const PasswordTab = () => {
  const [passError, setPassError] = useState("");
  const [loading, setLoading] = useState(false);
  const { token } = useSelector((state) => state.logInUser);
  const [form] = Form.useForm();

  const handlePasswordChange = async (values) => {
    if (values?.newPassword === values.currentPassword) {
      return setPassError("Your old password cannot be your new password.");
    }
    if (values?.newPassword !== values?.confirmPassword) {
      return setPassError("Confirm password doesn't match.");
    } else {
      setPassError("");
    }

    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          old_password: values.currentPassword,
          new_password: values.newPassword
        })
      });
      const data = await response.json();
      
      if (response.ok) {
        message.success("Password changed successfully!");
        form.resetFields();
      } else {
        setPassError(data.detail || "Failed to change password.");
      }
    } catch (error) {
      message.error("Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Form form={form} layout="vertical" onFinish={handlePasswordChange}>
        <h2 className="text-xl font-semibold mb-4 text-center">
          Change Your Password
        </h2>

        <Form.Item
          name="currentPassword"
          label="Old Password"
          rules={[
            { required: true, message: "Please enter your current password!" },
          ]}
        >
          <Input.Password style={{ padding: "9px", borderRadius: "0px" }} placeholder="Old Password" />
        </Form.Item>

        <Form.Item
          name="newPassword"
          label="New Password"
          rules={[{ required: true, message: "Please enter a new password!" }]}
        >
          <Input.Password  style={{ padding: "9px", borderRadius: "0px" }} placeholder="New Password" />
        </Form.Item>

        <Form.Item
          name="confirmPassword"
          label="Confirm New Password"
          dependencies={["newPassword"]}
          rules={[
            { required: true, message: "Please confirm your new password!" },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue("newPassword") === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error("Passwords do not match!"));
              },
            }),
          ]}
        >
          <Input.Password style={{ padding: "9px", borderRadius: "0px" }} placeholder="Confirm Password" />
        </Form.Item>

        {/* Display error if password validations fail */}
        {passError && <p className="text-[#8B4513] text-sm mb-2">{passError}</p>}

        <Form.Item>
          <div className="flex justify-center">
          <button type="submit" disabled={loading} className={`w-full bg-[#8B4513] text-white py-2 ${loading ? "opacity-70" : ""}`}>
                {loading ? "Changing..." : "Change Password"}
              </button>
          </div>
        </Form.Item>
      </Form>
    </div>
  );
};