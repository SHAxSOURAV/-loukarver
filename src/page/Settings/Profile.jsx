import { useState, useEffect } from "react";
import { Avatar, Form, Input, message } from "antd";
import { IoCameraOutline } from "react-icons/io5";
import { PasswordTab } from "./PasswordTab";

import { useSelector } from "react-redux";

const Profile = () => {
  const [activeTab, setActiveTab] = useState("1");
  const [form] = Form.useForm();
  const [image, setImage] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const { token } = useSelector((state) => state.logInUser);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setProfile(data);
        form.setFieldsValue({
          name: data.name,
          email: data.email,
        });
      }
    } catch (error) {
      console.error("Error fetching profile:", error);
    }
  };

  const handleImageChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Show preview immediately
    setImage(file);
    
    // Upload image to backend
    const formData = new FormData();
    formData.append("file", file);

    try {
      // Assuming we use our generic upload endpoint we created, or /users/photo
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (response.ok && data.url) {
        // Now save the URL to the user's profile in the DB
        const patchResponse = await fetch(`${import.meta.env.VITE_BACKEND_URL}/users/me`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            profile_photo_url: data.url
          }),
        });
        
        if (patchResponse.ok) {
          message.success("Profile photo uploaded!");
          fetchProfile(); // Refresh profile to get updated photo URL
        } else {
          message.error("Failed to save profile photo to DB");
        }
      } else {
        message.error(data.detail || "Failed to upload photo");
      }
    } catch (error) {
      message.error("Error uploading photo");
      console.error(error);
    }
  };

  const onEditProfile = async (values) => {
    setLoading(true);
    try {
      // You can implement the backend PUT /users/profile call here if you want to update name
      // For now, let's just mock it or assume it calls the relationships endpoint
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/users/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: values.name,
        }),
      });
      
      const data = await response.json();
      if (response.ok) {
        message.success("Profile updated successfully");
        fetchProfile();
      } else {
        message.error(data.detail || "Failed to update profile");
      }
    } catch (error) {
      message.error("Error updating profile");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    {
      key: "1",
      label: "Edit Profile",
      content: (
        <Form onFinish={onEditProfile} layout="vertical" form={form}>
          <Form.Item name="name" label="Name">
            <Input
              style={{ padding: "9px", borderRadius: "0px" }}
              placeholder="Enter name"
              rules={[{ required: true, message: "Please enter your name" }]}
            />
          </Form.Item>

          <Form.Item name="email" label="Email">
            <Input
              disabled
              style={{ padding: "9px", borderRadius: "0px" }}
              placeholder="Enter Email"
            />
          </Form.Item>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#8B4513] text-white py-2 rounded-md hover:bg-opacity-90 transition"
          >
            {loading ? "Updating..." : "Update"}
          </button>
        </Form>
      ),
    },
    {
      key: "2",
      label: "Change Password",
      content: <PasswordTab />,
    },
  ];

  const getProfileImage = () => {
    if (image) return URL.createObjectURL(image);
    if (profile?.profile_photo_url) return profile.profile_photo_url;
    return "https://via.placeholder.com/140";
  };

  return (
    <div className="p-3 bg-white min-h-screen">
      <div className="">
        <div className="max-w-xl mx-auto mt-8 rounded-lg p-6 ">
          {/* Profile Picture Section */}
          <div className="text-center mb-6">
            <div className="relative w-[140px] h-[124px] mx-auto">
              <input
                type="file"
                onChange={handleImageChange}
                id="img"
                style={{ display: "none" }}
                accept="image/*"
              />
              <img
                style={{ width: 140, height: 140, borderRadius: "100%", objectFit: "cover" }}
                src={getProfileImage()}
                alt="Admin Profile"
              />
              {activeTab === "1" && (
                <label
                  htmlFor="img"
                  className="absolute top-[80px] -right-2 bg-white rounded-full w-8 h-8 flex items-center justify-center cursor-pointer shadow border border-gray-100"
                >
                  <IoCameraOutline className="text-black " />
                </label>
              )}
            </div>

            <p className="text-lg font-semibold mt-4">{profile?.name || "Admin"}</p>
          </div>

          {/* Custom Tabs Section */}
          <div className="mb-4">
            <div className="flex space-x-6 justify-center mb-4 border-b">
              {tabItems.map((item) => (
                <button
                  key={item.key}
                  className={`py-2 font-medium ${
                    activeTab === item.key
                      ? "border-b-2 border-[#8B4513] text-[#8B4513]"
                      : "text-gray-500 hover:text-black"
                  }`}
                  onClick={() => setActiveTab(item.key)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div className="mt-6">
              {tabItems.find((item) => item.key === activeTab)?.content}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
